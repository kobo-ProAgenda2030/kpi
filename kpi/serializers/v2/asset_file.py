# coding: utf-8
import base64
import json
import os
from mimetypes import guess_type
from typing import Union
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.validators import (
    URLValidator,
    ValidationError as DjangoValidationError,
)
from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.reverse import reverse

from kpi.fields import (
    RelativePrefixHyperlinkedRelatedField,
    SerializerMethodFileField,
    WritableJSONField,
)
from kpi.models.asset_file import AssetFile


class AssetFileSerializer(serializers.ModelSerializer):
    uid = serializers.ReadOnlyField()
    url = serializers.SerializerMethodField()
    asset = RelativePrefixHyperlinkedRelatedField(
        view_name='asset-detail', lookup_field='uid', read_only=True)
    user = RelativePrefixHyperlinkedRelatedField(
        view_name='user-detail', lookup_field='username', read_only=True)
    user__username = serializers.ReadOnlyField(source='user.username')
    file_type = serializers.ChoiceField(choices=AssetFile.TYPE_CHOICES)
    description = serializers.CharField()
    date_created = serializers.ReadOnlyField()
    content = SerializerMethodFileField(allow_empty_file=True, required=False)
    metadata = WritableJSONField(required=False)

    class Meta:
        model = AssetFile
        fields = (
            'uid',
            'url',
            'asset',
            'user',
            'user__username',
            'file_type',
            'description',
            'date_created',
            'content',
            'metadata',
        )

    def get_url(self, obj):
        return reverse('asset-file-detail',
                       args=(obj.asset.uid, obj.uid),
                       request=self.context.get('request', None))

    def get_content(self, obj, *args, **kwargs):
        return reverse('asset-file-content',
                       args=(obj.asset.uid, obj.uid),
                       request=self.context.get('request', None))

    def to_internal_value(self, data):
        """
        Overrides parent method to add base64 encoded string to validated data
        if it exists.
        """
        ret = super().to_internal_value(data)
        # `base64Encoded` is not a valid field, thus it is discarded by Django
        # validation process. We add it here to be able to access it in
        # `.validate()` and use our custom validation.
        try:
            ret['base64_encoded'] = data['base64Encoded']
        except KeyError:
            pass
        return ret

    def validate(self, attr):
        self.__file_type = attr['file_type']

        metadata = self._get_metadata(attr.get('metadata'))
        validated_field = self._validate_media_content_method(attr, metadata)
        # Call the validator related to `validated_field`, either:
        # - `self._validate_content()`
        # - `self._validate_base64_encoded()`
        # - `self._validate_redirect_url()`
        validator = getattr(self, f'_validate_{validated_field}')
        validator(attr, metadata)

        # Common validators
        filename = metadata['filename']
        self.__validate_mime_type(filename, validated_field)
        self.__validate_extension(filename, validated_field)
        self._validate_duplicate(filename, validated_field)

        # Remove `'base64_encoded'` from attributes passed to the model
        attr.pop('base64_encoded', None)

        return attr

    def _get_metadata(self, metadata: Union[str, dict]) -> dict:
        """
        `metadata` parameter can be sent as a stringified JSON or in pure JSON.
        """
        if not isinstance(metadata, dict):
            try:
                metadata = json.loads(metadata)
            except ValueError:
                raise serializers.ValidationError({
                    'metadata': _('JSON is invalid')
                })

        return metadata

    def _validate_base64_encoded(self, attr: dict, metadata: dict):
        base64_encoded = attr['base64_encoded']
        metadata = self._validate_metadata(metadata)

        try:
            media_content = base64_encoded[base64_encoded.index('base64') + 7:]
        except ValueError:
            raise serializers.ValidationError({
                'base64Encoded': _('Invalid content')
            })

        attr.update({
            'content': ContentFile(base64.decodebytes(media_content.encode()),
                                   name=metadata['filename'])
        })

    def _validate_content(self, attr: dict, metadata: dict):
        try:
            attr['content']
        except KeyError:
            raise serializers.ValidationError({
                'content': _('No files have been submitted')
            })

        metadata['filename'] = attr['content'].name

    def _validate_duplicate(self, filename: str, field_name: str):

        if self.__file_type == AssetFile.FORM_MEDIA:
            view = self.context.get('view')
            asset = getattr(view, 'asset', self.context.get('asset'))
            # File name must be unique
            if AssetFile.objects.filter(asset=asset,
                                        deleted_at__isnull=True,
                                        metadata__filename=filename).exists():
                error = self.__format_error(field_name,
                                            _('File already exists'))
                raise serializers.ValidationError(error)

    def _validate_media_content_method(self,
                                       attr: dict,
                                       metadata: dict) -> str:
        """
        Validates whether user only uses one of the available methods to
        save a media file:
        - Binary upload
        - Base64 encoded string
        - Remote URL

        Raises an `ValidationError` otherwise

        Returns:
            str: 'content', 'base64_encoded', 'redirect_url'
        """
        methods = []
        try:
            metadata['redirect_url']
        except KeyError:
            pass
        else:
            methods.append('redirect_url')

        try:
            attr['base64_encoded']
        except KeyError:
            pass
        else:
            methods.append('base64_encoded')

        try:
            attr['content']
        except KeyError:
            # if no other methods are used, force binary upload for later
            # validation
            if not methods:
                methods.append('content')
        else:
            methods.append('content')

        # Only one method should be present
        if len(methods) == 1:
            return methods[0]

        raise serializers.ValidationError(
            {
                'detail': _(
                    'You can upload media file with two '
                    'different ways at the same time. Please choose '
                    'between binary upload, base64 or remote URL.'
                )
            }
        )

    def _validate_metadata(self,
                           metadata: dict,
                           validate_redirect_url: bool = False) -> dict:
        if not metadata:
            raise serializers.ValidationError({
                'metadata': _('This field is required')
            })

        if validate_redirect_url:
            try:
                metadata['redirect_url']
            except KeyError:
                raise serializers.ValidationError({
                    'metadata': _('`redirect_url` is required')
                })
            else:
                parsed_url = urlparse(metadata['redirect_url'])
                metadata['filename'] = os.path.basename(parsed_url.path)

        try:
            metadata['filename']
        except KeyError:
            raise serializers.ValidationError({
                'metadata': _('`filename` is required')
            })

        return metadata

    def _validate_redirect_url(self, attr: dict, metadata: dict):
        metadata = self._validate_metadata(metadata, validate_redirect_url=True)

        redirect_url = metadata['redirect_url']
        validator = URLValidator()
        try:
            validator(redirect_url)
        except (AttributeError, DjangoValidationError):
            raise serializers.ValidationError({
                'metadata': _('`redirect_url` is invalid')
            })

    # PRIVATE METHODS
    # These methods could protected too but IMO, they should not be
    # overridden if a class inherits from `AssetFileSerializer`
    def __format_error(self, field_name: str, message: str):
        """
        Formats validation error to return explicit field name.
        For example, if `redirect_url` is being validated, we

        """
        if field_name == 'redirect_url':
            field_name = 'metadata'
            message = f'`redirect_url`: {message}'

        return {field_name: message}

    def __validate_extension(self, filename: str, field_name: str):
        """
        Validates extension of the file depending on its type
        (`form_media` or `media_layer`)
        """
        try:
            allowed_extensions = AssetFile.ALLOWED_EXTENSIONS[self.__file_type]
        except KeyError:
            pass
        else:
            basename, file_extension = os.path.splitext(filename)
            if file_extension not in allowed_extensions:
                extensions_csv = '`, `'.join(allowed_extensions)
                error = self.__format_error(
                    field_name,
                    _('Only `{}` extensions are allowed').format(extensions_csv)
                )
                raise serializers.ValidationError(error)

    def __validate_mime_type(self, source: str, field_name: str):
        """
        Validates MIME type of the file depending on its type
        (`form_media` or `media_layer`)
        Args:
            source (str): Can be the base64 encoded string, the name of the
                          file or the URL
            field_name (str): name of field to return in case of validation
                              error
        """
        # Check if content type is allowed
        try:
            allowed_mime_types = AssetFile.ALLOWED_MIME_TYPES[self.__file_type]
        except KeyError:
            pass
        else:
            mime_type, _ = guess_type(source)
            if not mime_type or not mime_type.startswith(allowed_mime_types):
                mime_types_csv = '`, `'.join(allowed_mime_types)
                error = self.__format_error(
                    field_name,
                    _('Only `{}` extensions are allowed').format(mime_types_csv)
                )
                raise serializers.ValidationError(error)

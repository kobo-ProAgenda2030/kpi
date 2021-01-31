 #!/bin/bash
rm -rf "./jsapp/fonts" &&
rm -rf "./jsapp/compiled" &&
npm run copy-fonts && npm run build &&
python manage.py collectstatic --noinput &&
git submodule init &&
git submodule update --remote &&
python manage.py compilemessages
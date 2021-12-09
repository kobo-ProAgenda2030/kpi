import React from 'react';
import PropTypes from 'prop-types';
import reactMixin from 'react-mixin';
import autoBind from 'react-autobind';
import Reflux from 'reflux';
import { Link } from 'react-router';
import {stores} from '../stores';
import {bem} from '../bem';
import {searches} from '../searches';
import mixins from '../mixins';
import LibrarySidebar from 'js/components/library/librarySidebar';
import {
  IntercomHelpBubble,
  SupportHelpBubble
} from '../components/helpBubbles';
import {
  COMMON_QUERIES,
  MODAL_TYPES,
  ROUTES,
} from '../constants';
import {assign} from 'utils';
import SidebarFormsList from '../lists/sidebarForms';

import {ShinyMenu} from 'kpi-custom-modules/lib/modules/shiny/ShinyMenu';
import {customSessionInstance} from 'kpi-custom-modules/lib/session/CustomSession'
import {SUPPORT_API_BASE_URL} from '../support-api-constants';

class FormSidebar extends Reflux.Component {
  constructor(props){
    super(props);
    this.state = assign({
      currentAssetId: false,
      files: []
    }, stores.pageState.state);
    this.stores = [
      stores.session,
      stores.pageState
    ];
    autoBind(this);
  }
  componentWillMount() {
    this.setStates();
  }
  setStates() {
    this.setState({
      headerFilters: 'forms',
      searchContext: searches.getSearchContext('forms', {
        filterParams: {
          assetType: COMMON_QUERIES.s,
        },
        filterTags: COMMON_QUERIES.s,
      })
    });
  }
  newFormModal (evt) {
    evt.preventDefault();
    stores.pageState.showModal({
      type: MODAL_TYPES.NEW_FORM
    });
  }
  render () {
    return (
      <React.Fragment>
        <bem.KoboButton onClick={this.newFormModal} m={['blue', 'fullwidth']}>
          {t('new')}
        </bem.KoboButton>
        <SidebarFormsList/>
      </React.Fragment>
    );
  }
  componentWillReceiveProps() {
    this.setStates();
  }

};

FormSidebar.contextTypes = {
  router: PropTypes.object
};

reactMixin(FormSidebar.prototype, searches.common);
reactMixin(FormSidebar.prototype, mixins.droppable);

class DrawerLink extends React.Component {
  constructor(props) {
    super(props);
    autoBind(this);
  }
  onClick (evt) {
    if (!this.props.href) {
      evt.preventDefault();
    }
    if (this.props.onClick) {
      this.props.onClick(evt);
    }
  }
  render () {
    var icon_class = (this.props['ki-icon'] == undefined ? 'fa fa-globe' : `k-icon-${this.props['ki-icon']}`);
    var icon = (<i className={icon_class}/>);
    var classNames = [this.props.class, 'k-drawer__link'];

    var link;
    if (this.props.linkto) {
      link = (
        <Link to={this.props.linkto}
            className={classNames.join(' ')}
            activeClassName='active'
            data-tip={this.props.label}>
          {icon}
        </Link>
      );
    } else {
      link = (
        <a href={this.props.href || '#'}
            className={classNames.join(' ')}
            onClick={this.onClick}
            data-tip={this.props.label}>
            {icon}
        </a>
      );
    }
    return link;
  }
}

class Drawer extends Reflux.Component {
  constructor(props){
    super(props);
    autoBind(this);
    this.stores = [
      stores.session,
      stores.pageState,
      stores.serverEnvironment,
    ];
  }
  render () {
    const showExtraMenu=(customSessionInstance.hasAccess("forms_view")||customSessionInstance.hasAccess("library_view")||customSessionInstance.hasAccess("shiny_dashboard"))
    &&
    (this.isLibrary()||this.isForms()||this.isShiny())
    return (
      <bem.KDrawer style={{ width: showExtraMenu ? 270 : 58 }}>
        <bem.KDrawer__primaryIcons>
          {customSessionInstance.hasAccess("forms_view") && <DrawerLink label={t('Projects')} linkto={ROUTES.FORMS} ki-icon='projects' />}
          {customSessionInstance.hasAccess("library_view") && <DrawerLink label={t('Library')} linkto={ROUTES.LIBRARY} ki-icon='library' />}
          {customSessionInstance.hasAccess("users_view") && <DrawerLink label={t('Users')} linkto='/users' ki-icon='people' />}
          {customSessionInstance.hasAccess("organizations_view") && <DrawerLink label={t('Organizations')} linkto='/organizations' ki-icon='graph-settings' />}
          {customSessionInstance.hasAccess("shiny_dashboard") && <DrawerLink label={t('Dashboard')} linkto='/shiny_dashboard' ki-icon='report' />}
        </bem.KDrawer__primaryIcons>
        {showExtraMenu&&
        <bem.KDrawer__sidebar>
          { this.isLibrary() && customSessionInstance.hasAccess("library_view")
            ? <LibrarySidebar />
              : this.isForms() && customSessionInstance.hasAccess("forms_view")?
                <FormSidebar />
                : this.isShiny() && customSessionInstance.hasAccess("shiny_dashboard")?
                  <ShinyMenu baseURL={`${SUPPORT_API_BASE_URL}`} />
                  : <div/>
          }
        </bem.KDrawer__sidebar>
        }
        {/* <bem.KDrawer__secondaryIcons>
          { stores.session.currentAccount &&
            <IntercomHelpBubble/>
          }
          { stores.session.currentAccount &&
            <SupportHelpBubble/>
          }
          { stores.session.currentAccount &&
            <a href={stores.session.currentAccount.projects_url}
              className='k-drawer__link'
              target='_blank'
              data-tip={t('Projects (legacy)')}
            >
              <i className='k-icon k-icon-globe' />
            </a>
          }
          { stores.serverEnvironment &&
            stores.serverEnvironment.state.source_code_url &&
            <a href={stores.serverEnvironment.state.source_code_url}
              className='k-drawer__link' target='_blank' data-tip={t('Source')}>
              <i className='k-icon k-icon-github' />
            </a>
          }
        </bem.KDrawer__secondaryIcons> */}
      </bem.KDrawer>
      );
  }
}

reactMixin(Drawer.prototype, searches.common);
reactMixin(Drawer.prototype, mixins.droppable);
reactMixin(Drawer.prototype, mixins.contextRouter);

Drawer.contextTypes = {
  router: PropTypes.object
};

export default Drawer;

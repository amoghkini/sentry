import PropTypes from 'prop-types';
import React from 'react';
import createReactClass from 'create-react-class';
import {browserHistory, Link} from 'react-router';
import qs from 'query-string';
import {omit, isEqual} from 'lodash';
import SentryTypes from 'app/proptypes';
import ApiMixin from 'app/mixins/apiMixin';
import GroupStore from 'app/stores/groupStore';
import LoadingError from 'app/components/loadingError';
import LoadingIndicator from 'app/components/loadingIndicator';
import Pagination from 'app/components/pagination';
import CompactIssue from 'app/components/compactIssue';
import EventUserReport from 'app/components/events/userReport';
import {Panel, PanelBody} from 'app/components/panels';
import EmptyStateWarning from 'app/components/emptyStateWarning';
import {t, tct} from 'app/locale';
import withEnvironmentInQueryString from 'app/utils/withEnvironmentInQueryString';

const ProjectUserReports = createReactClass({
  displayName: 'ProjectUserReports',

  propTypes: {
    defaultQuery: PropTypes.string,
    defaultStatus: PropTypes.string,
    setProjectNavSection: PropTypes.func,
    environment: SentryTypes.Environment,
  },

  mixins: [ApiMixin],

  getDefaultProps() {
    return {
      defaultQuery: '',
      defaultStatus: 'unresolved',
    };
  },

  getInitialState() {
    return {
      reportList: [],
      loading: true,
      error: false,
      pageLinks: '',
      query: this.props.defaultQuery,
      status: this.props.defaultStatus,
      environment: this.props.environment,
      ...this.getQueryStringState(this.props),
    };
  },

  componentWillMount() {
    this.props.setProjectNavSection('user-feedback');
    this.fetchData();
  },

  componentWillReceiveProps(nextProps) {
    // Ignore changes to environment term since this is handled separately
    const nextSearchTerm = omit(qs.parse(nextProps.location.search), 'environment');
    const thisSearchTerm = omit(qs.parse(this.props.location.search), 'environment');

    if (!isEqual(nextSearchTerm, thisSearchTerm)) {
      this.setState(this.getQueryStringState(nextProps), this.fetchData);
    }

    if (nextProps.environment !== this.props.environment) {
      this.setState(
        {
          environment: nextProps.environment,
        },
        this.fetchData
      );
    }
  },

  getQueryStringState(props) {
    let q = props.location.query;
    let status = 'status' in q ? q.status : this.props.defaultStatus;
    let query = 'query' in q ? q.query : this.props.defaultQuery;

    return {
      query,
      status,
    };
  },

  onSearch(query) {
    let targetQueryParams = {};
    if (query !== '') targetQueryParams.query = query;
    if (this.state.status !== this.props.defaultStatus)
      targetQueryParams.status = this.state.status;

    let {orgId, projectId} = this.props.params;
    browserHistory.push({
      pathname: `/${orgId}/${projectId}/user-feedback/`,
      query: targetQueryParams,
    });
  },

  fetchData() {
    this.setState({
      loading: true,
      error: false,
    });

    let params = this.props.params;

    let query = {
      ...this.props.location.query,
      limit: 50,
      query: this.state.query,
      status: this.state.status,
    };

    if (this.state.environment) {
      query.environment = this.state.environment.name;
    } else {
      delete query.environment;
    }

    this.api.request(`/projects/${params.orgId}/${params.projectId}/user-reports/`, {
      query,
      success: (data, _, jqXHR) => {
        let issues = data.map(r => r.issue);
        GroupStore.add(issues);
        this.setState({
          error: false,
          loading: false,
          reportList: data,
          pageLinks: jqXHR.getResponseHeader('Link'),
        });
      },
      error: () => {
        this.setState({
          error: true,
          loading: false,
        });
      },
    });
  },

  getUserReportsUrl() {
    let params = this.props.params;

    return `/${params.orgId}/${params.projectId}/settings/user-feedback/`;
  },

  renderStreamBody() {
    if (this.state.loading) {
      return <LoadingIndicator />;
    } else if (this.state.error) {
      return <LoadingError onRetry={this.fetchData} />;
    } else if (this.state.reportList.length > 0) {
      return this.renderResults();
    } else if (this.state.query && this.state.query !== this.props.defaultQuery) {
      return this.renderNoQueryResults();
    } else {
      return this.renderEmpty();
    }
  },

  renderNoQueryResults() {
    return (
      <EmptyStateWarning>
        <p>{t('Sorry, no results match your search query.')}</p>
      </EmptyStateWarning>
    );
  },

  renderEmpty() {
    const {environment} = this.state;
    const message = environment
      ? tct('No user reports have been collected from your [env] environment.', {
          env: environment.displayName,
        })
      : t('No user reports have been collected.');
    return (
      <EmptyStateWarning>
        <p>{message}</p>
        <p>
          <Link to={this.getUserReportsUrl()}>
            {t('Learn how to integrate User Feedback')}
          </Link>
        </p>
      </EmptyStateWarning>
    );
  },

  renderResults() {
    const {orgId, projectId} = this.props.params;

    const children = this.state.reportList.map(item => {
      const issue = item.issue;

      return (
        <CompactIssue
          key={item.id}
          id={issue.id}
          data={issue}
          orgId={orgId}
          projectId={projectId}
        >
          <EventUserReport
            report={item}
            orgId={orgId}
            projectId={projectId}
            issueId={issue.id}
          />
        </CompactIssue>
      );
    });

    return children;
  },

  render() {
    let path = this.props.location.pathname;
    let status = this.state.status;
    return (
      <div>
        <div className="row release-list-header">
          <div className="col-sm-9">
            <h3>{t('User Feedback')}</h3>
          </div>
          <div className="col-sm-3" style={{textAlign: 'right'}}>
            <div className="btn-group">
              <Link
                to={path}
                className={
                  'btn btn-sm btn-default' + (status === 'unresolved' ? ' active' : '')
                }
              >
                {t('Unresolved')}
              </Link>
              <Link
                to={{pathname: path, query: {status: ''}}}
                className={'btn btn-sm btn-default' + (status === '' ? ' active' : '')}
              >
                {t('All Issues')}
              </Link>
            </div>
          </div>
        </div>
        <Panel>
          <PanelBody className="issue-list">{this.renderStreamBody()}</PanelBody>
        </Panel>
        <Pagination pageLinks={this.state.pageLinks} />
      </div>
    );
  },
});

export {ProjectUserReports};
export default withEnvironmentInQueryString(ProjectUserReports);

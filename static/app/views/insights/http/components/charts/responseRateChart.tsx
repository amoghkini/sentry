import type {Series} from 'sentry/types/echarts';
import {formatPercentage} from 'sentry/utils/number/formatPercentage';
import {MutableSearch} from 'sentry/utils/tokenizeSearch';
import {
  HTTP_RESPONSE_3XX_COLOR,
  HTTP_RESPONSE_4XX_COLOR,
  HTTP_RESPONSE_5XX_COLOR,
} from 'sentry/views/insights/colors';
import Chart, {ChartType} from 'sentry/views/insights/common/components/chart';
import ChartPanel from 'sentry/views/insights/common/components/chartPanel';
import {DataTitles} from 'sentry/views/insights/common/views/spans/types';
import {ALERTS} from 'sentry/views/insights/http/alerts';
import {CHART_HEIGHT} from 'sentry/views/insights/http/settings';
import type {SpanMetricsQueryFilters} from 'sentry/views/insights/types';

interface Props {
  isLoading: boolean;
  series: [Series, Series, Series];
  error?: Error | null;
  filters?: SpanMetricsQueryFilters;
}

export function ResponseRateChart({series, isLoading, error, filters}: Props) {
  const filterString = filters && MutableSearch.fromQueryObject(filters).formatString();
  const alertConfig = [
    {...ALERTS.threeHundreds, query: filterString ?? ALERTS.threeHundreds.query},
    {...ALERTS.fourHundreds, query: filterString ?? ALERTS.fourHundreds.query},
    {...ALERTS.fiveHundreds, query: filterString ?? ALERTS.fiveHundreds.query},
  ];
  return (
    <ChartPanel title={DataTitles.unsuccessfulHTTPCodes} alertConfigs={alertConfig}>
      <Chart
        showLegend
        height={CHART_HEIGHT}
        grid={{
          left: '4px',
          right: '0',
          top: '8px',
          bottom: '0',
        }}
        data={series}
        loading={isLoading}
        error={error}
        chartColors={[
          HTTP_RESPONSE_3XX_COLOR,
          HTTP_RESPONSE_4XX_COLOR,
          HTTP_RESPONSE_5XX_COLOR,
        ]}
        type={ChartType.LINE}
        aggregateOutputFormat="percentage"
        dataMax={getAxisMaxForPercentageSeries(series)}
        tooltipFormatterOptions={{
          valueFormatter: value => formatPercentage(value),
        }}
      />
    </ChartPanel>
  );
}

/**
 * Given a set of `Series` objects that contain percentage data (i.e., every item in `data` has a `value` between 0 and 1) return an appropriate max value.
 *
 * e.g., for series with very low values (like 5xx rates), it rounds to the nearest significant digit. For other cases, it limits it to 100
 */
export function getAxisMaxForPercentageSeries(series: Series[]): number {
  const maxValue = Math.max(
    ...series.map(serie => Math.max(...serie.data.map(datum => datum.value)))
  );

  const maxNumberOfDecimalPlaces = Math.ceil(Math.min(0, Math.log10(maxValue)));

  return Math.pow(10, maxNumberOfDecimalPlaces);
}

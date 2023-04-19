import {Fragment} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Location} from 'history';

import {Series} from 'sentry/types/echarts';
import Chart from 'sentry/views/starfish/components/chart';

const HOST = 'http://localhost:8080';

type Props = {
  location: Location;
};

export default function CacheModuleView({}: Props) {
  const GRAPH_QUERY = `
  select operation,
       count() as count,
       toStartOfInterval(start_timestamp, INTERVAL 1 DAY) as interval
  from default.spans_experimental_starfish
  where module = 'cache'
 group by interval,
          operation
  order by interval, operation
  `;
  const TOTALS_QUERY = `
  select operation,
       sum(exclusive_time) as count,
       toStartOfInterval(start_timestamp, INTERVAL 1 DAY) as interval
  from default.spans_experimental_starfish
  where module = 'cache'
 group by interval,
          operation
  order by interval, operation
  `;

  const {isLoading: isGraphLoading, data: graphData} = useQuery({
    queryKey: ['graph'],
    queryFn: () => fetch(`${HOST}/?query=${GRAPH_QUERY}`).then(res => res.json()),
    retry: false,
    initialData: [],
  });
  const {isLoading: isTopGraphLoading, data: totalsQueryGraphData} = useQuery({
    queryKey: ['topGraph'],
    queryFn: () => fetch(`${HOST}/?query=${TOTALS_QUERY}`).then(res => res.json()),
    retry: false,
    initialData: [],
  });

  const seriesByOperation: {[operation: string]: Series} = {};
  graphData.forEach(datum => {
    seriesByOperation[datum.operation] = {
      seriesName: datum.operation,
      data: [],
    };
  });

  graphData.forEach(datum => {
    seriesByOperation[datum.operation].data.push({
      value: datum.count,
      name: datum.interval,
    });
  });

  const data = Object.values(seriesByOperation);

  const seriesByOperation2: {[operation: string]: Series} = {};
  totalsQueryGraphData.forEach(datum => {
    seriesByOperation2[datum.operation] = {
      seriesName: datum.operation,
      data: [],
    };
  });

  totalsQueryGraphData.forEach(datum => {
    seriesByOperation2[datum.operation].data.push({
      value: datum.count,
      name: datum.interval,
    });
  });

  const data2 = Object.values(seriesByOperation2);

  return (
    <Fragment>
      Time spent per operation
      <Chart
        statsPeriod="24h"
        height={180}
        data={data2}
        start=""
        end=""
        loading={isTopGraphLoading}
        utc={false}
        grid={{
          left: '0',
          right: '0',
          top: '16px',
          bottom: '8px',
        }}
        disableMultiAxis
        definedAxisTicks={4}
        isLineChart
      />
      Throughput
      <Chart
        statsPeriod="24h"
        height={180}
        data={data}
        start=""
        end=""
        loading={isGraphLoading}
        utc={false}
        grid={{
          left: '0',
          right: '0',
          top: '16px',
          bottom: '8px',
        }}
        disableMultiAxis
        definedAxisTicks={4}
        isLineChart
      />
    </Fragment>
  );
}

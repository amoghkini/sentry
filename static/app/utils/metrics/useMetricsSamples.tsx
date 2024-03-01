import {normalizeDateTimeParams} from 'sentry/components/organizations/pageFilters/parse';
import type {DateString, MRI, PageFilters} from 'sentry/types';
import {useApiQuery} from 'sentry/utils/queryClient';
import useOrganization from 'sentry/utils/useOrganization';
import usePageFilters from 'sentry/utils/usePageFilters';

/**
 * This type is incomplete as there are other fields available.
 */
type FieldTypes = {
  id: string;
  profile_id: string | undefined;
  project: string;
  'span.description': string;
  'span.duration': number;
  'span.op': string;
  'span.self_time': number;
  timestamp: DateString;
  trace: string;
  'transaction.id': string;
};

export type Summary = {
  count: number;
  max: number;
  min: number;
  sum: number;
};

type ResultFieldTypes = FieldTypes & {
  summary: Summary;
};

export type Field = keyof FieldTypes;
export type ResultField = keyof ResultFieldTypes;

interface UseMetricSamplesOptions<F extends Field> {
  fields: F[];
  referrer: string;
  datetime?: PageFilters['datetime'];
  enabled?: boolean;
  limit?: number;
  max?: number;
  min?: number;
  mri?: MRI;
  query?: string;
  sort?: string;
}

export interface MetricsSamplesResults<F extends Field> {
  data: Pick<ResultFieldTypes, F | 'summary'>[];
  meta: any; // not going to type this yet
}

export function useMetricsSamples<F extends Field>({
  datetime,
  enabled,
  fields,
  limit,
  max,
  min,
  mri,
  referrer,
  query,
  sort,
}: UseMetricSamplesOptions<F>) {
  const organization = useOrganization();
  const {selection} = usePageFilters();

  const path = `/organizations/${organization.slug}/metrics/samples/`;

  const endpointOptions = {
    query: {
      project: selection.projects,
      environment: selection.environments,
      ...(datetime ?? normalizeDateTimeParams(selection.datetime)),
      field: fields,
      max,
      min,
      mri,
      query,
      referrer,
      per_page: limit,
      sort,
    },
  };

  return useApiQuery<MetricsSamplesResults<F>>([path, endpointOptions], {
    staleTime: 0,
    refetchOnWindowFocus: false,
    retry: false,
    enabled,
  });
}

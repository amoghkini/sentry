import styled from '@emotion/styled';

import {pinFilter} from 'sentry/actionCreators/pageFilters';
import type {ButtonProps} from 'sentry/components/button';
import {Button} from 'sentry/components/button';
import {IconLock} from 'sentry/icons';
import {t} from 'sentry/locale';
import type {PinnedPageFilter} from 'sentry/types/core';
import type {Organization} from 'sentry/types/organization';
import {trackAnalytics} from 'sentry/utils/analytics';
import usePageFilters from 'sentry/utils/usePageFilters';

type Props = {
  filter: PinnedPageFilter;
  organization: Organization;
  size: Extract<ButtonProps['size'], 'xs' | 'zero'>;
  className?: string;
};

function PageFilterPinButton({organization, filter, size, className}: Props) {
  const {pinnedFilters} = usePageFilters();
  const pinned = pinnedFilters.has(filter);

  const onPin = () => {
    trackAnalytics('page_filters.pin_click', {
      organization,
      filter,
      pin: !pinned,
    });
    pinFilter(filter, !pinned);
  };

  return (
    <PinButton
      className={className}
      aria-pressed={pinned}
      aria-label={t('Lock filter')}
      onClick={onPin}
      size={size}
      pinned={pinned}
      borderless={size === 'zero'}
      icon={<IconLock locked={pinned} size="xs" />}
      title={t("Once locked, Sentry will remember this filter's value across pages.")}
      tooltipProps={{delay: 500}}
    >
      {pinned ? t('Locked') : t('Lock')}
    </PinButton>
  );
}

const PinButton = styled(Button)<{pinned: boolean; size: 'xs' | 'zero'}>`
  display: block;
  color: ${p => p.theme.textColor};

  :hover {
    color: ${p => p.theme.headingColor};
  }
  ${p => p.size === 'zero' && 'background: transparent'};
`;

export default PageFilterPinButton;

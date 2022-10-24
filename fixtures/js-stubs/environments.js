module.exports.Environments = function (hidden) {
  if (hidden) {
    return [{id: '1', name: 'zzz', isHidden: true}];
  }
  return [
    {id: '1', name: 'production', displayName: 'Production', isHidden: false},
    {id: '2', name: 'staging', displayName: 'Staging', isHidden: false},
    {id: '3', name: 'STAGING', displayName: 'STAGING', isHidden: true},
  ];
};

class AdsConfig {
  const AdsConfig._();

  static const bannerAdUnitId = String.fromEnvironment('ADMOB_BANNER_ID');

  static bool get isConfigured => bannerAdUnitId.isNotEmpty;
}

import 'package:google_mobile_ads/google_mobile_ads.dart';

import 'ads_config.dart';

Future<void> initializeAds() async {
  if (!AdsConfig.isConfigured) return;
  await MobileAds.instance.initialize();
}

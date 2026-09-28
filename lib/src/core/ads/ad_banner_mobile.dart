import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import 'ad_consent_store.dart';

class AdBanner extends StatefulWidget {
  const AdBanner({super.key});

  @override
  State<AdBanner> createState() => _AdBannerState();
}

class _AdBannerState extends State<AdBanner> {
  BannerAd? banner;
  bool? consent;

  @override
  void initState() {
    super.initState();
    _loadConsent();
  }

  Future<void> _loadConsent() async {
    final accepted = await AdConsentStore().hasConsent();
    if (!mounted) return;
    setState(() => consent = accepted);
    if (!accepted) return;
    banner = BannerAd(
      adUnitId: const String.fromEnvironment('ADMOB_BANNER_ID', defaultValue: 'ca-app-pub-3940256099942544/6300978111'),
      size: AdSize.banner,
      request: const AdRequest(),
      listener: BannerAdListener(onAdFailedToLoad: (ad, error) => ad.dispose()),
    )..load();
  }

  @override
  void dispose() {
    banner?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (consent == false) {
      return TextButton.icon(onPressed: () async { await AdConsentStore().grantConsent(); await _loadConsent(); }, icon: const Icon(Icons.ads_click), label: const Text('Aceptar anuncios personalizados'));
    }
    if (consent == null) return const SizedBox(height: 50);
    final currentBanner = banner;
    if (currentBanner == null) return const SizedBox(height: 50);
    return SizedBox(height: currentBanner.size.height.toDouble(), width: currentBanner.size.width.toDouble(), child: AdWidget(ad: currentBanner));
  }
}

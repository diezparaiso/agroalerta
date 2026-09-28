import 'package:shared_preferences/shared_preferences.dart';

class AdConsentStore {
  Future<bool> hasConsent() async => (await SharedPreferences.getInstance()).getBool('agroalerta.ad_consent') ?? false;
  Future<void> grantConsent() async => (await SharedPreferences.getInstance()).setBool('agroalerta.ad_consent', true);
  Future<void> revokeConsent() async => (await SharedPreferences.getInstance()).setBool('agroalerta.ad_consent', false);
}

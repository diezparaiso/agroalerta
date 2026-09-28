import 'package:shared_preferences/shared_preferences.dart';

class LocalDataManager {
  Future<void> deleteUserData(String userId) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove('agroalerta.parcels.$userId');
    await preferences.remove('agroalerta.pending_reports');
    await preferences.remove('agroalerta.notifications');
    await preferences.remove('agroalerta.offline');
    await preferences.remove('agroalerta.ad_consent');
  }
}

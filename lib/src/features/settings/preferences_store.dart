import 'package:shared_preferences/shared_preferences.dart';

class PreferencesStore {
  Future<bool> notificationsEnabled() async => (await SharedPreferences.getInstance()).getBool('agroalerta.notifications') ?? true;
  Future<bool> offlineCacheEnabled() async => (await SharedPreferences.getInstance()).getBool('agroalerta.offline') ?? true;
  Future<void> setNotificationsEnabled(bool value) async => (await SharedPreferences.getInstance()).setBool('agroalerta.notifications', value);
  Future<void> setOfflineCacheEnabled(bool value) async => (await SharedPreferences.getInstance()).setBool('agroalerta.offline', value);
}

import 'package:shared_preferences/shared_preferences.dart';

class ProfileStore {
  Future<bool> isComplete(String userId) async => (await SharedPreferences.getInstance()).getBool('agroalerta.profile.$userId.complete') ?? false;

  Future<void> save(String userId, String comarca, Set<String> crops) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool('agroalerta.profile.$userId.complete', true);
    await preferences.setString('agroalerta.profile.$userId.comarca', comarca);
    await preferences.setStringList('agroalerta.profile.$userId.crops', crops.toList());
  }
}

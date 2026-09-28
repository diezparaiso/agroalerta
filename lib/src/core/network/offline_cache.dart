import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class OfflineCache {
  Future<void> save(String key, Object value) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(key, jsonEncode(value));
  }

  Future<dynamic> read(String key) async {
    final preferences = await SharedPreferences.getInstance();
    final value = preferences.getString(key);
    return value == null ? null : jsonDecode(value);
  }
}

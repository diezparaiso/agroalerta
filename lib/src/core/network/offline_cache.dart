import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Small key/value cache for non-sensitive API responses.
///
/// This cache is device-local and is not a source of truth. Callers own cache
/// key versioning, freshness policy, and user/parcel scoping.
class OfflineCache {
  Future<void> save(String key, Object value) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(key, jsonEncode(value));
  }

  /// Returns null for a cache miss or an unreadable entry.
  ///
  /// Corrupt entries are removed so they cannot fail repeatedly. Cache errors
  /// must not turn a recoverable API error into an unrelated JSON parsing error.
  Future<dynamic> read(String key) async {
    final preferences = await SharedPreferences.getInstance();
    final value = preferences.getString(key);
    if (value == null) return null;

    try {
      return jsonDecode(value);
    } on FormatException {
      await preferences.remove(key);
      return null;
    }
  }

  Future<void> remove(String key) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(key);
  }
}

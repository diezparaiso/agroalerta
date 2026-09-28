import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'parcel_provider.dart';

class LocalParcelStore {
  Future<List<ParcelSummary>> read(String userId) async {
    final preferences = await SharedPreferences.getInstance();
    final raw = preferences.getString('agroalerta.parcels.$userId');
    if (raw == null) return [];
    final records = (jsonDecode(raw) as List<dynamic>).cast<Map<String, dynamic>>();
    return records.map(ParcelSummary.fromJson).toList();
  }

  Future<void> write(String userId, List<ParcelSummary> parcels) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('agroalerta.parcels.$userId', jsonEncode([for (final parcel in parcels) parcel.toJson()]));
  }
}

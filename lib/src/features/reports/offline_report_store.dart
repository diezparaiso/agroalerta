import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'offline_retry_policy.dart';

class OfflineReportStore {
  Future<void> enqueue(Map<String, dynamic> report) async {
    final preferences = await SharedPreferences.getInstance();
    final pending = await readAll();
    pending.add(OfflineRetryPolicy.normalize(report));
    await preferences.setString('agroalerta.pending_reports', jsonEncode(pending));
  }

  Future<List<Map<String, dynamic>>> readAll() async {
    final preferences = await SharedPreferences.getInstance();
    final raw = jsonDecode(preferences.getString('agroalerta.pending_reports') ?? '[]') as List<dynamic>;
    return raw
        .map((item) => OfflineRetryPolicy.normalize(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<void> replace(List<Map<String, dynamic>> reports) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(
      'agroalerta.pending_reports',
      jsonEncode(reports.map(OfflineRetryPolicy.normalize).toList()),
    );
  }
}

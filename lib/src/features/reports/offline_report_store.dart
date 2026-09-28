import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class OfflineReportStore {
  Future<void> enqueue(Map<String, dynamic> report) async {
    final preferences = await SharedPreferences.getInstance();
    final pending = (jsonDecode(preferences.getString('agroalerta.pending_reports') ?? '[]') as List<dynamic>).cast<Map<String, dynamic>>();
    pending.add(report);
    await preferences.setString('agroalerta.pending_reports', jsonEncode(pending));
  }

  Future<List<Map<String, dynamic>>> readAll() async {
    final preferences = await SharedPreferences.getInstance();
    return (jsonDecode(preferences.getString('agroalerta.pending_reports') ?? '[]') as List<dynamic>).cast<Map<String, dynamic>>();
  }

  Future<void> replace(List<Map<String, dynamic>> reports) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('agroalerta.pending_reports', jsonEncode(reports));
  }
}

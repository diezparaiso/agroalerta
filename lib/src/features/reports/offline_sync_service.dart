import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';

import '../../core/network/api_client.dart';
import 'offline_report_store.dart';
import 'offline_retry_policy.dart';

class OfflineSyncService {
  OfflineSyncService({ApiClient? apiClient, OfflineReportStore? store})
      : _apiClient = apiClient ?? ApiClient(),
        _store = store ?? OfflineReportStore();

  final ApiClient _apiClient;
  final OfflineReportStore _store;
  StreamSubscription<List<ConnectivityResult>>? _subscription;
  bool _syncing = false;

  void start() {
    _subscription ??= Connectivity().onConnectivityChanged.listen((results) {
      if (results.any((result) => result != ConnectivityResult.none)) {
        sync();
      }
    });
  }

  Future<void> sync() async {
    if (_syncing) return;
    _syncing = true;
    try {
      final now = DateTime.now().toUtc();
      final pending = await _store.readAll();
      final remaining = <Map<String, dynamic>>[];

      for (final report in pending) {
        if (!OfflineRetryPolicy.isEligible(report, now: now)) {
          remaining.add(report);
          continue;
        }

        try {
          await _apiClient.submitRawFieldReport(report);
        } catch (_) {
          remaining.add(
            OfflineRetryPolicy.markFailure(report, now: DateTime.now().toUtc()),
          );
        }
      }

      await _store.replace(remaining);
    } finally {
      _syncing = false;
    }
  }

  Future<void> dispose() async => _subscription?.cancel();
}

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'offline_queue_status.dart';
import 'offline_report_store.dart';

final offlineQueueStatusProvider = FutureProvider.autoDispose<OfflineQueueStatus>((ref) async {
  final reports = await OfflineReportStore().readAll();
  return summarizeOfflineQueue(reports);
});

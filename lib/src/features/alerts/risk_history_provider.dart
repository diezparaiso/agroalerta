import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final riskHistoryProvider = FutureProvider.family<List<RiskHistoryPoint>, String>((ref, parcelId) async {
  final records = await ref.read(apiClientProvider).getRiskHistory(parcelId);
  return [for (final record in records) RiskHistoryPoint(score: (record['risk_score'] as num?)?.toDouble() ?? 0)];
});

class RiskHistoryPoint {
  const RiskHistoryPoint({required this.score});
  final double score;
}

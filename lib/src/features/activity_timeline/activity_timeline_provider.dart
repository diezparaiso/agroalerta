import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../parcels/parcel_provider.dart';

final selectedTimelineParcelProvider = StateProvider<String?>((ref) => null);

final activityTimelineProvider = FutureProvider<List<Map<String, dynamic>>>((ref) {
  final parcelId = ref.watch(selectedTimelineParcelProvider);
  if (parcelId == null) return Future.value(const []);
  return ref.watch(apiClientProvider).getActivityTimeline(parcelId);
});

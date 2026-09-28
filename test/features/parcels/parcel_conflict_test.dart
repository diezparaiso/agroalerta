import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/parcels/parcel_conflict.dart';

void main() {
  test('conflict summary detects changed fields', () {
    const summary = ParcelConflictSummary(
      localLabel: 'Finca local',
      remoteLabel: 'Finca servidor',
      localCrop: 'Olivar',
      remoteCrop: 'Olivar',
      localComarca: 'Campiña',
      remoteComarca: 'Campiña',
    );

    expect(summary.hasDifferences, isTrue);
  });

  test('identical versions have no field differences', () {
    const summary = ParcelConflictSummary(
      localLabel: 'Finca',
      remoteLabel: 'Finca',
      localCrop: 'Olivar',
      remoteCrop: 'Olivar',
      localComarca: 'Campiña',
      remoteComarca: 'Campiña',
    );

    expect(summary.hasDifferences, isFalse);
  });
}

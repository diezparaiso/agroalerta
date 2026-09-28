import 'package:flutter_test/flutter_test.dart';
import 'package:agroalerta_andalucia/src/features/home/telemetry_provider.dart';

void main() {
  test('telemetry windows compare by duration', () {
    expect(const TelemetryWindow(24), const TelemetryWindow(24));
    expect(const TelemetryWindow(24), isNot(const TelemetryWindow(168)));
  });
  test('telemetrySeries orders real measurements chronologically', () {
    final history = [
      {'temperature_c': 22.0, 'measured_at': '2026-09-28T12:00:00Z'},
      {'temperature_c': 20.0, 'measured_at': '2026-09-28T10:00:00Z'},
      {'temperature_c': 21.0, 'measured_at': '2026-09-28T11:00:00Z'},
    ];
    final series = telemetrySeries(history, 'temperature_c');
    expect(series.map((item) => item['temperature_c']), [20.0, 21.0, 22.0]);
  });

  test('telemetrySeries ignores missing measurements instead of inventing values', () {
    final history = [
      {'measured_at': '2026-09-28T12:00:00Z'},
      {'temperature_c': 21.0, 'measured_at': '2026-09-28T11:00:00Z'},
      {'temperature_c': 'unknown', 'measured_at': '2026-09-28T10:00:00Z'},
    ];
    final series = telemetrySeries(history, 'temperature_c');
    expect(series, hasLength(1));
    expect(series.single['temperature_c'], 21.0);
  });
  test('telemetrySeries can isolate a selected sensor', () {
    final history = [
      {'device_id': 'sensor-a', 'temperature_c': 20.0, 'measured_at': '2026-09-28T10:00:00Z'},
      {'device_id': 'sensor-b', 'temperature_c': 30.0, 'measured_at': '2026-09-28T11:00:00Z'},
    ];

    final series = telemetrySeries(history, 'temperature_c', deviceId: 'sensor-a');

    expect(series, hasLength(1));
    expect(series.single['temperature_c'], 20.0);
  });
}


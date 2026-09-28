import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/home/weather_provider.dart';

void main() {
  group('weatherDisplayValue', () {
    test('renders a real value when present', () {
      expect(
        weatherDisplayValue({'temperature_c': 21.5}, 'temperature_c'),
        '21.5',
      );
    });

    test('does not invent a value when evidence is absent', () {
      expect(
        weatherDisplayValue({'source': 'none'}, 'temperature_c'),
        'No disponible',
      );
    });
  });
}

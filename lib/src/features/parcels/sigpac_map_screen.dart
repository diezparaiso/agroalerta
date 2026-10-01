import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../core/network/api_client.dart';
import 'parcel_provider.dart';

class SigpacMapScreen extends ConsumerStatefulWidget {
  const SigpacMapScreen({super.key});

  @override
  ConsumerState<SigpacMapScreen> createState() => _SigpacMapScreenState();
}

class _SigpacMapScreenState extends ConsumerState<SigpacMapScreen> {
  final _west = TextEditingController(text: '-6.1');
  final _south = TextEditingController(text: '37.2');
  final _east = TextEditingController(text: '-5.8');
  final _north = TextEditingController(text: '37.5');
  Map<String, dynamic>? _collection;
  String? _selectedId;
  bool _loading = false;
  bool _importing = false;
  String? _error;
  String? _message;

  @override
  void dispose() {
    _west.dispose();
    _south.dispose();
    _east.dispose();
    _north.dispose();
    super.dispose();
  }

  String get _bbox => '${_west.text.trim()},${_south.text.trim()},${_east.text.trim()},${_north.text.trim()}';

  Future<void> _search() async {
    setState(() { _loading = true; _error = null; _message = null; });
    try {
      final result = await ref.read(apiClientProvider).searchSigpacRecintos(bbox: _bbox, limit: 100);
      if (result['type'] != 'FeatureCollection' || result['features'] is! List) {
        throw const FormatException('La API no devolvió una FeatureCollection GeoJSON válida.');
      }
      setState(() {
        _collection = result;
        final features = result['features'] as List;
        _selectedId = features.isEmpty ? null : _featureId(features.first as Map<String, dynamic>);
      });
    } catch (error) {
      setState(() { _collection = null; _error = 'No se pudieron consultar los recintos. Comprueba la extensión, el backend y la conexión. Detalle: $error'; });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _importArea() async {
    setState(() { _importing = true; _error = null; _message = null; });
    try {
      final result = await ref.read(apiClientProvider).importSigpacRecintos(bbox: _bbox, limit: 100);
      setState(() => _message = 'Importación completada: ${result['imported'] ?? 0} nuevos y ${result['updated'] ?? 0} actualizados. La operación afecta a los resultados del área, no solo al recinto seleccionado.');
    } catch (error) {
      setState(() => _error = 'No se pudo importar el área: $error');
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }

  String _featureId(Map<String, dynamic> feature) => (feature['id'] ?? feature['properties']?['id'] ?? 'recinto-${(feature['properties'] ?? {}).hashCode}').toString();

  List<LatLng> _polygonPoints(Map<String, dynamic> feature) {
    final geometry = feature['geometry'];
    if (geometry is! Map || geometry['type'] != 'Polygon') return const [];
    final coordinates = geometry['coordinates'];
    if (coordinates is! List || coordinates.isEmpty || coordinates.first is! List) return const [];
    return (coordinates.first as List).whereType<List>().where((point) => point.length >= 2 && point[0] is num && point[1] is num).map((point) => LatLng((point[1] as num).toDouble(), (point[0] as num).toDouble())).toList();
  }

  @override
  Widget build(BuildContext context) {
    final features = (_collection?['features'] as List? ?? const []).whereType<Map<String, dynamic>>().toList();
    final polygons = <Polygon>[];
    for (final feature in features) {
      final points = _polygonPoints(feature);
      if (points.length >= 3) {
        polygons.add(Polygon(
          points: points,
          color: _featureId(feature) == _selectedId ? Colors.green.withValues(alpha: 0.35) : Colors.blue.withValues(alpha: 0.18),
          borderColor: _featureId(feature) == _selectedId ? Colors.green.shade800 : Colors.blue.shade700,
          borderStrokeWidth: _featureId(feature) == _selectedId ? 3 : 1.5,
        ));
      }
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Importar recintos SIGPAC')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Consulta por extensión geográfica (WGS84). La búsqueda está limitada a 100 resultados por petición.', style: TextStyle(fontSize: 14)),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _coordinateField('Oeste', _west), _coordinateField('Sur', _south),
          _coordinateField('Este', _east), _coordinateField('Norte', _north),
        ]),
        const SizedBox(height: 12),
        Wrap(spacing: 8, children: [
          FilledButton.icon(onPressed: _loading ? null : _search, icon: const Icon(Icons.search), label: Text(_loading ? 'Consultando…' : 'Buscar recintos')),
          FilledButton.tonalIcon(onPressed: _importing ? null : _importArea, icon: const Icon(Icons.download), label: Text(_importing ? 'Importando…' : 'Importar área')),
        ]),
        if (_error != null) ...[const SizedBox(height: 12), Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))],
        if (_message != null) ...[const SizedBox(height: 12), Text(_message!, style: TextStyle(color: Theme.of(context).colorScheme.primary))],
        const SizedBox(height: 12),
        SizedBox(height: 360, child: ClipRRect(borderRadius: BorderRadius.circular(12), child: FlutterMap(
          options: const MapOptions(initialCenter: LatLng(37.35, -5.95), initialZoom: 10),
          children: [
            TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', userAgentPackageName: 'es.agroalerta.andalucia'),
            PolygonLayer(polygons: polygons),
          ],
        ))),
        const SizedBox(height: 8),
        Text('Resultados: ${features.length}', style: Theme.of(context).textTheme.titleMedium),
        if (features.isEmpty && !_loading) const Padding(padding: EdgeInsets.all(12), child: Text('Todavía no hay resultados. Ajusta el área y pulsa «Buscar recintos».')),
        for (final feature in features)
          Card(
            child: ListTile(
              selected: _featureId(feature) == _selectedId,
              leading: Icon(_featureId(feature) == _selectedId ? Icons.radio_button_checked : Icons.radio_button_unchecked),
              title: Text((feature['properties']?['recinto'] ?? feature['id'] ?? 'Recinto sin identificador').toString()),
              subtitle: Text((feature['properties'] ?? {}).entries.take(3).map((entry) => '${entry.key}: ${entry.value}').join(' · ')),
              onTap: () => setState(() => _selectedId = _featureId(feature)),
            ),
          ),
        const SizedBox(height: 12),
        const Text('La selección sirve para inspeccionar un recinto en esta pantalla. El contrato actual de importación recibe un bbox e importa los resultados del área; no importa únicamente el elemento seleccionado. Los polígonos MultiPolygon no se dibujan todavía.', style: TextStyle(fontSize: 12)),
      ]),
    );
  }

  Widget _coordinateField(String label, TextEditingController controller) => SizedBox(
    width: 130,
    child: TextField(controller: controller, keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true), decoration: InputDecoration(labelText: label, border: const OutlineInputBorder())),
  );
}

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

class RiskHistoryChart extends StatelessWidget {
  const RiskHistoryChart({this.spots, super.key});

  final List<FlSpot>? spots;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return SizedBox(
      height: 190,
      child: LineChart(
        LineChartData(
          minY: 0,
          maxY: 1,
          gridData: const FlGridData(show: true),
          titlesData: const FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineBarsData: [LineChartBarData(isCurved: true, color: color, barWidth: 3, dotData: const FlDotData(show: true), spots: spots ?? const [FlSpot(0, .18), FlSpot(1, .26), FlSpot(2, .31), FlSpot(3, .48), FlSpot(4, .58)])],
        ),
      ),
    );
  }
}

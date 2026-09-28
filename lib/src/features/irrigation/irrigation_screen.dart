import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import '../parcels/parcel_provider.dart';

class IrrigationScreen extends ConsumerStatefulWidget {
  const IrrigationScreen({super.key});
  @override ConsumerState<IrrigationScreen> createState() => _IrrigationScreenState();
}
class _IrrigationScreenState extends ConsumerState<IrrigationScreen> {
  String? parcelId;
  Map<String,dynamic>? data;
  bool loading=false;
  Future<void> load() async {
    if(parcelId==null)return;
    setState(()=>loading=true);
    try { final value=await ref.read(apiClientProvider).getIrrigationIntelligence(parcelId!); if(mounted)setState(()=>data=value); }
    finally { if(mounted)setState(()=>loading=false); }
  }
  @override Widget build(BuildContext context) {
    final parcels=ref.watch(parcelsProvider);
    return AppPage(title:'Inteligencia hídrica',subtitle:'Histórico de riego y estado de humedad',child:parcels.when(
      loading:()=>const Center(child:CircularProgressIndicator()),
      error:(e,_)=>Center(child:Text('Error: '+e.toString())),
      data:(items)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Row(children:[
          DropdownButton<String>(value:parcelId,hint:const Text('Parcela'),items:[for(final p in items)DropdownMenuItem(value:p.id,child:Text(p.name))],onChanged:(v)=>setState(()=>parcelId=v)),
          const SizedBox(width:12),
          FilledButton(onPressed:loading?null:load,child:const Text('Consultar')),
        ]),
        if(loading)const LinearProgressIndicator(),
        if(data!=null)Expanded(child:ListView(children:[
          Card(child:ListTile(title:Text('Estado: '+(data!['soil_status']?.toString()??'')),subtitle:Text((data!['explanation']?.toString()??'')+'\nAcción: '+(data!['action']?.toString()??'')))),
          Card(child:ListTile(title:Text('Agua registrada: '+(data!['total_water_liters']?.toString()??'0')+' L'),subtitle:Text('Eventos: '+(data!['event_count']?.toString()??'0')+' · Nivel de uso: '+(data!['water_use_level']?.toString()??'')))),
          Text('Evidencias',style:Theme.of(context).textTheme.titleLarge),
          ...((data!['evidence'] as List<dynamic>? ?? const []).map((e)=>ListTile(leading:const Icon(Icons.water_drop_outlined),title:Text(e.toString())))),
        ])),
      ],
    ));
  }
}

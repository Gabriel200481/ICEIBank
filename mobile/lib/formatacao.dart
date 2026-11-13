String dinheiro(double valor) {
  final negativo = valor < 0;
  final partes = valor.abs().toStringAsFixed(2).split('.');
  final inteiro = partes[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => '.');
  return '${negativo ? '-' : ''}R\$ $inteiro,${partes[1]}';
}

String hora(DateTime d) =>
    '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}:${d.second.toString().padLeft(2, '0')}';

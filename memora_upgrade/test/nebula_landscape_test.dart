import 'package:flutter_test/flutter_test.dart';
import 'package:memora/nebula_art.dart';

void main() {
  test('Nébula chooses landscapes from location before biome', () {
    expect(nebulaLandscapeKey('Distrito de los puentes','mercado'),'scene_puentes');
    expect(nebulaLandscapeKey('Plaza del reloj','mercado'),'scene_plaza');
    expect(nebulaLandscapeKey('Archivo de la luna','torre'),'scene_archivo');
    expect(nebulaLandscapeKey('Puerto imperial','mercado'),'scene_puerto');
    expect(nebulaLandscapeKey('Tesorería real','torre'),'scene_tesoreria');
    expect(nebulaLandscapeKey('Nuevo lugar','forja'),'scene_forja');
  });
}

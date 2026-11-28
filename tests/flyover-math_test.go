package mth
import ("testing";"math")
func TestMapSlopPureMath(t *testing.T){
 if TileCountPerAxis(5)!=32 {t.Fatal("tile count")}
 x,y:=LatLonToTileOSM(2,0,0);if x!=2||y!=2{t.Fatal(x,y)}
 x,y=LatLonToTileTMS(2,0,0);if x!=2||y!=2{t.Fatal(x,y)}
 if math.Abs(EarthRadiusByLatitude(0)-6378137)>1e-6{t.Fatal("equator")}
 if math.Abs(EarthRadiusByLatitude(90)-6356752.314245179)>1e-6{t.Fatal("pole")}
 r:=QuaternionToMatrix(0,0,0,1);if r!=[9]float64{1,0,0,0,1,0,0,0,1}{t.Fatal(r)}
}

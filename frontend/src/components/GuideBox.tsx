import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** "Come procedere" workflow reminder, shown only when suggestions exist. */
export function GuideBox() {
  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Come procedere</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
          <li>Applica i suggerimenti in ordine di priorità (P1 → P5).</li>
          <li>Dopo ogni modifica, ricarica la traccia per verificare il delta.</li>
          <li>Ripeti finché i suggerimenti si riducono a zero.</li>
        </ol>
      </CardContent>
    </Card>
  );
}

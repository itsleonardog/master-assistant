import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO: replace with the actual repository URL before publishing.
const GITHUB_URL = "https://github.com/itsleonardog/master-assistant";

interface LandingPageProps {
  onEnterApp: () => void;
}

const STEPS: string[] = [
  "Carica la tua traccia non masterizzata e una reference commerciale dello stesso genere.",
  "L'app analizza loudness, spettro e immagine stereo, e li confronta con la reference.",
  "Ricevi suggerimenti concreti: quale plugin, quale parametro, di quanto. Specifici per la tua DAW.",
  "Applichi, ricarichi, iteri. Con la pratica, i suggerimenti diventano superflui: il tuo orecchio è abbastanza.",
];

/**
 * Marketing landing page: explains the project mission and gates the analyzer
 * behind an explicit call to action. Owns no app state.
 */
export function LandingPage({ onEnterApp }: LandingPageProps) {
  const currentYear = new Date().getFullYear();

  function scrollToMission() {
    document.getElementById("mission")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="bg-muted/20">
        <div className="mx-auto max-w-4xl px-6 py-12 md:py-20">
          <Badge variant="secondary">Open source · Educativo</Badge>
          <h1 className="mt-4 max-w-3xl text-3xl font-bold tracking-tight md:text-5xl">
            Il mastering, spiegato ai producer.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            Analizza la tua traccia contro una reference commerciale. Ricevi suggerimenti concreti
            per la tua DAW. Impara a masterizzare in autonomia, una traccia alla volta.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" onClick={onEnterApp}>
              Apri l'analizzatore →
            </Button>
            <Button size="lg" variant="outline" onClick={scrollToMission}>
              Cos'è questo progetto?
            </Button>
          </div>
        </div>
      </section>

      <section id="mission" className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">La nostra missione</h2>
        <p className="mt-4 text-base text-muted-foreground">
          Crediamo che il mastering di qualità non debba essere riservato a chi ha uno studio
          professionale. Milioni di home producer producono musica eccellente che non riesce a
          competere a livello sonoro perché manca un passaggio di mastering fatto bene. Vogliamo
          colmare quel divario con la conoscenza, non con la magia.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Per chi è fatto</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Home producer che vogliono chiudere i propri brani con un master competitivo, senza
                dover imparare un mestiere da zero.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Come funziona</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Carichi la tua traccia e una reference commerciale. L'app misura loudness, spettro e
                immagine stereo. Ti dice esattamente cosa sistemare, con quali plugin della tua DAW
                nativa.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="my-16 px-6">
        <Alert className="mx-auto max-w-4xl border-l-4 border-primary bg-muted/30 p-6">
          <h3 className="text-xl font-bold">Non masterizziamo per te.</h3>
          <p className="mt-2 text-base text-muted-foreground">
            Nessun algoritmo magico. Nessun 'carica e scarica il master pronto'. Gli strumenti
            automatici ti danno un file — noi ti diamo la comprensione di come arrivarci. Se cerchi
            un pulsante che faccia tutto, questo progetto non fa per te. Se vuoi imparare a farlo,
            benvenuto.
          </p>
        </Alert>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">Come funziona, in 4 passi</h2>
        <ol className="mt-8 space-y-6">
          {STEPS.map((step, index) => (
            <li key={step} className="flex items-start gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground">
                {index + 1}
              </span>
              <p className="text-base text-muted-foreground">{step}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">Uno scopo educativo</h2>
        <p className="mt-4 text-base text-muted-foreground">
          Ogni suggerimento include il perché: cosa stai correggendo, in che misura, e che effetto
          avrà. Non impari a memoria 'se hai X dB taglia Y Hz', impari a riconoscere cosa suona
          storto e cosa fare. È un percorso. Con tanta pratica, i suggerimenti diventano superflui:
          il tuo orecchio è abbastanza.
        </p>
      </section>

      <section className="bg-muted/20">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <h2 className="text-2xl font-semibold tracking-tight">Open source, per davvero</h2>
          <p className="mt-4 text-base text-muted-foreground">
            Il codice è aperto. Puoi leggerlo, forkarlo, migliorarlo. Se sai programmare, proponi
            una pull request. Se sai masterizzare, condividi i tuoi casi d'uso. Se stai imparando,
            segnala cosa non funziona. Ogni contributo rende lo strumento migliore per tutti.
          </p>
          <Button variant="outline" asChild className="mt-6">
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              Vedi su GitHub ↗
            </a>
          </Button>
        </div>
      </section>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        Fatto per home producer · Open source · {currentYear}
      </footer>
    </main>
  );
}

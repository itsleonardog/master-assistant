/** Page heading and one-line description. */
export function Header() {
  return (
    <header className="space-y-2 text-center sm:text-left">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Master Assistant</h1>
      <p className="text-sm text-muted-foreground sm:text-base">
        Confronta la tua traccia con un riferimento e ottieni suggerimenti di mastering pronti per
        il tuo DAW.
      </p>
    </header>
  );
}

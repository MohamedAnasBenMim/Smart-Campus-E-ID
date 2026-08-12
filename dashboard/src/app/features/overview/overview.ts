import { Component, OnInit, OnDestroy, signal, computed, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { Zones } from '../../core/services/zones';
import { Personnes } from '../../core/services/personnes';
import { Evenements } from '../../core/services/evenements';
import { Alertes } from '../../core/services/alertes';
import { Auth } from '../../core/auth';
import { EvenementAcces, Alerte } from '../../core/models';

const LIBELLES_ALERTE: Record<string, { label: string; classe: string; icone: string }> = {
  SPOOFING: { label: 'Tentative de spoofing', classe: 'alerte-critique', icone: 'gpp_bad' },
  ACCES_NON_AUTORISE: { label: 'Personne inconnue', classe: 'alerte-critique', icone: 'person_off' },
  ACCES_INTERDIT: { label: 'Zone non autorisée', classe: 'alerte-moyenne', icone: 'block' },
  HORAIRE_INTERDIT: { label: 'Hors horaire', classe: 'alerte-moyenne', icone: 'schedule' },
  PRESENCE_NON_IDENTIFIEE: { label: 'Présence non identifiée', classe: 'alerte-moyenne', icone: 'visibility_off' },
  IDENTITE_A_CONFIRMER: { label: 'Identité à confirmer', classe: 'alerte-faible', icone: 'help' },
};

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './overview.html',
  styleUrl: './overview.scss',
})
export class Overview implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('videoPreview') videoPreview?: ElementRef<HTMLVideoElement>;

  now = signal(new Date());

  nbZones = signal<number | null>(null);
  nbPersonnes = signal<number | null>(null);
  nbEvenements = signal<number | null>(null);
  nbAlertesActives = signal<number | null>(null);
  nbAccordes = signal(0);
  nbRefuses = signal(0);

  dernieresAlertes = signal<Alerte[]>([]);
  derniersEvenements = signal<EvenementAcces[]>([]);

  camDisponible = signal(true);

  // Circonférence du cercle SVG (r=70) — sert à dessiner l'anneau de progression
  private readonly rayonAnneau = 70;
  readonly circonference = 2 * Math.PI * this.rayonAnneau;

  tauxAccorde = computed(() => {
    const total = this.nbAccordes() + this.nbRefuses();
    return total === 0 ? 0 : Math.round((this.nbAccordes() / total) * 100);
  });

  decalageAnneau = computed(() => this.circonference * (1 - this.tauxAccorde() / 100));

  salutation = computed(() => {
    const heure = this.now().getHours();
    if (heure < 12) return 'Bonjour';
    if (heure < 18) return 'Bon après-midi';
    return 'Bonsoir';
  });

  formattedDate = computed(() =>
    this.now().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }),
  );
  formattedTime = computed(() => this.now().toLocaleTimeString('fr-FR'));

  private refreshInterval?: ReturnType<typeof setInterval>;
  private clockInterval?: ReturnType<typeof setInterval>;
  private mediaStream?: MediaStream;

  constructor(
    public auth: Auth,
    private zonesService: Zones,
    private personnesService: Personnes,
    private evenementsService: Evenements,
    private alertesService: Alertes,
  ) {}

  libelleAlerte(type: string): string {
    return LIBELLES_ALERTE[type]?.label ?? type;
  }

  classeAlerte(type: string): string {
    return LIBELLES_ALERTE[type]?.classe ?? 'alerte-faible';
  }

  iconeAlerte(type: string): string {
    return LIBELLES_ALERTE[type]?.icone ?? 'error_outline';
  }

  tempsEcoule(dateStr: string): string {
    const secondes = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
    if (secondes < 60) return "à l'instant";
    const minutes = Math.floor(secondes / 60);
    if (minutes < 60) return `il y a ${minutes} min`;
    const heures = Math.floor(minutes / 60);
    if (heures < 24) return `il y a ${heures} h`;
    return `il y a ${Math.floor(heures / 24)} j`;
  }

  ngOnInit(): void {
    this.chargerDonnees();
    this.refreshInterval = setInterval(() => this.chargerDonnees(), 10_000);
    this.clockInterval = setInterval(() => this.now.set(new Date()), 30_000);
  }

  ngAfterViewInit(): void {
    this.demarrerCamera();
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
    if (this.clockInterval) clearInterval(this.clockInterval);
    this.mediaStream?.getTracks().forEach((track) => track.stop());
  }

  private chargerDonnees(): void {
    this.zonesService.lister().subscribe((zones) => this.nbZones.set(zones.length));
    this.personnesService.lister().subscribe((personnes) => this.nbPersonnes.set(personnes.length));

    this.evenementsService.lister().subscribe((evenements) => {
      this.nbEvenements.set(evenements.length);
      this.nbAccordes.set(evenements.filter((e) => e.resultat === 'ACCORDE').length);
      this.nbRefuses.set(evenements.filter((e) => e.resultat === 'REFUSE').length);
      this.derniersEvenements.set(
        [...evenements]
          .sort((a, b) => new Date(b.horodatage).getTime() - new Date(a.horodatage).getTime())
          .slice(0, 6),
      );
    });

    this.alertesService.lister().subscribe((alertes) => {
      const actives = alertes.filter((a) => a.statut === 'NON_TRAITEE');
      this.nbAlertesActives.set(actives.length);
      this.dernieresAlertes.set(
        actives
          .sort((a, b) => new Date(b.horodatage).getTime() - new Date(a.horodatage).getTime())
          .slice(0, 5),
      );
    });
  }

  private demarrerCamera(): void {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.camDisponible.set(false);
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then((stream) => {
        this.mediaStream = stream;
        if (this.videoPreview) {
          this.videoPreview.nativeElement.srcObject = stream;
        }
      })
      .catch(() => this.camDisponible.set(false));
  }
}
import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { Evenements } from '../../core/services/evenements';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { Zones as ZonesService } from '../../core/services/zones';
import { EvenementAcces, Personne, Zone } from '../../core/models';
import { ImageLightbox } from '../../shared/components/image-lightbox/image-lightbox';

type Filtre = 'TOUS' | 'ACCORDE' | 'REFUSE';

@Component({
  selector: 'app-historique',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './historique.html',
  styleUrl: './historique.scss',
})
export class HistoriquePage implements OnInit {
  evenements = signal<EvenementAcces[]>([]);
  personnes = signal<Personne[]>([]);
  zones = signal<Zone[]>([]);
  chargement = signal(true);
  filtre = signal<Filtre>('TOUS');

  evenementsAffiches = computed(() => {
    const tries = [...this.evenements()].sort(
      (a, b) => new Date(b.horodatage).getTime() - new Date(a.horodatage).getTime(),
    );
    if (this.filtre() === 'TOUS') return tries;
    return tries.filter((e) => e.resultat === this.filtre());
  });

  nbAccordes = computed(() => this.evenements().filter((e) => e.resultat === 'ACCORDE').length);
  nbRefuses = computed(() => this.evenements().filter((e) => e.resultat === 'REFUSE').length);

  constructor(
    private evenementsService: Evenements,
    private personnesService: PersonnesService,
    private zonesService: ZonesService,
    private dialog: MatDialog,
  ) {}

  agrandir(evenement: EvenementAcces): void {
    if (!evenement.capturePhoto) return;
    this.dialog.open(ImageLightbox, {
      panelClass: 'lightbox-panel',
      backdropClass: 'lightbox-backdrop',
      maxWidth: '95vw',
      data: {
        imageUrl: evenement.capturePhoto,
        legende: `${this.nomPersonne(evenement.personneId)} — ${this.nomZone(evenement.zoneId)}`,
      },
    });
  }

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.zonesService.lister().subscribe((z) => this.zones.set(z));
    this.evenementsService.lister().subscribe({
      next: (evenements) => {
        this.evenements.set(evenements);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  nomPersonne(id: string | null): string {
    if (!id) return 'Personne non identifiée';
    const p = this.personnes().find((x) => x.id === id);
    return p ? `${p.nom} ${p.prenom ?? ''}`.trim() : 'Personne inconnue';
  }

  roleFor(id: string | null): string | null {
    if (!id) return null;
    return this.personnes().find((x) => x.id === id)?.role ?? null;
  }

  nomZone(id: string): string {
    return this.zones().find((z) => z.id === id)?.nom ?? 'Zone inconnue';
  }
}
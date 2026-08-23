import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog } from '@angular/material/dialog';
import { CoursService } from '../../core/services/cours';
import { ClassesService } from '../../core/services/classes';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { Zones as ZonesService } from '../../core/services/zones';
import { Cours, Classe, Personne, Zone } from '../../core/models';
import { FaireAppelDialog, DonneesFaireAppel } from './faire-appel-dialog';

const JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI'];
const HEURE_DEBUT_GRILLE = 8; // 8h00
const HEURE_FIN_GRILLE = 18; // 18h00
const MINUTES_PAR_CRENEAU = 15;
const CRENEAUX_TOTAL = ((HEURE_FIN_GRILLE - HEURE_DEBUT_GRILLE) * 60) / MINUTES_PAR_CRENEAU;

interface BlocCours {
  cours: Cours;
  colonne: number; // 1 = LUNDI ... 6 = SAMEDI
  ligneDebut: number;
  ligneFin: number;
  couleur: string;
}

type Vue = 'SEMAINE' | 'JOUR';

// Palette de couleurs stables, dérivées du nom du cours — pour
// distinguer visuellement les matières d'un coup d'œil.
const PALETTE = ['#7c6fdb', '#0e8f6b', '#c9822a', '#d64550', '#0090c4', '#9c6ade'];

@Component({
  selector: 'app-emploi-du-temps',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonToggleModule,
  ],
  templateUrl: './emploi-du-temps.html',
  styleUrl: './emploi-du-temps.scss',
})
export class EmploiDuTempsPage implements OnInit {
  classes = signal<Classe[]>([]);
  personnes = signal<Personne[]>([]);
  zones = signal<Zone[]>([]);
  tousLesCours = signal<Cours[]>([]);
  chargement = signal(true);

  classeSelectionneeId = signal<string | null>(null);
  vue = signal<Vue>('SEMAINE');
  jourSelectionne = signal<string>(this.jourDuJourOuLundi());

  jours = JOURS;

  coursDeLaClasse = computed(() => {
    const id = this.classeSelectionneeId();
    if (!id) return [];
    return this.tousLesCours().filter((c) => c.classeId === id);
  });

  blocs = computed<BlocCours[]>(() => {
    return this.coursDeLaClasse().map((c) => this.construireBloc(c));
  });

  blocsDuJour = computed<BlocCours[]>(() => {
    return this.blocs()
      .filter((b) => b.cours.jourSemaine === this.jourSelectionne())
      .sort((a, b) => a.ligneDebut - b.ligneDebut);
  });

  heuresAffichees = Array.from({ length: HEURE_FIN_GRILLE - HEURE_DEBUT_GRILLE }, (_, i) => HEURE_DEBUT_GRILLE + i);
  creneauxTotal = CRENEAUX_TOTAL;

  constructor(
    private coursService: CoursService,
    private classesService: ClassesService,
    private personnesService: PersonnesService,
    private zonesService: ZonesService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.zonesService.lister().subscribe((z) => this.zones.set(z));
    this.coursService.lister().subscribe((c) => this.tousLesCours.set(c));
    this.classesService.lister().subscribe({
      next: (classes) => {
        this.classes.set(classes);
        if (classes.length > 0 && !this.classeSelectionneeId()) {
          this.classeSelectionneeId.set(classes[0].id);
        }
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  nomPersonne(id: string): string {
    const p = this.personnes().find((x) => x.id === id);
    return p ? `${p.nom} ${p.prenom ?? ''}`.trim() : 'Inconnu';
  }

  nomZone(id: string): string {
    return this.zones().find((z) => z.id === id)?.nom ?? 'Zone inconnue';
  }

  /**
   * NOUVEAU — ouvre le dialogue "Faire l'appel" pour ce cours,
   * à la date du jour. Le pré-remplissage est calculé côté backend
   * à partir des événements d'accès déjà enregistrés.
   */
  ouvrirAppel(bloc: BlocCours): void {
    const aujourdHui = new Date().toISOString().substring(0, 10); // "YYYY-MM-DD"

    const donnees: DonneesFaireAppel = {
      coursId: bloc.cours.id,
      coursNom: bloc.cours.nom,
      date: aujourdHui,
      personnes: this.personnes(),
    };

    this.dialog.open(FaireAppelDialog, {
      width: '520px',
      maxHeight: '85vh',
      panelClass: 'app-dialog',
      data: donnees,
    });
  }

  private construireBloc(cours: Cours): BlocCours {
    const colonne = JOURS.indexOf(cours.jourSemaine) + 1;
    const ligneDebut = this.calculerLigne(cours.heureDebut);
    const ligneFin = this.calculerLigne(cours.heureFin);
    const couleur = PALETTE[this.hashSimple(cours.id) % PALETTE.length];

    return { cours, colonne, ligneDebut, ligneFin, couleur };
  }

  private calculerLigne(heure: string): number {
    const [h, m] = heure.split(':').map(Number);
    const minutesDepuisDebut = (h - HEURE_DEBUT_GRILLE) * 60 + m;
    return Math.max(1, Math.floor(minutesDepuisDebut / MINUTES_PAR_CRENEAU) + 1);
  }

  private hashSimple(texte: string): number {
    let h = 0;
    for (let i = 0; i < texte.length; i++) {
      h = (h * 31 + texte.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  private jourDuJourOuLundi(): string {
    const index = new Date().getDay(); // 0 = dimanche, 1 = lundi...
    const correspondance: Record<number, string> = {
      1: 'LUNDI',
      2: 'MARDI',
      3: 'MERCREDI',
      4: 'JEUDI',
      5: 'VENDREDI',
      6: 'SAMEDI',
    };
    return correspondance[index] ?? 'LUNDI';
  }
}
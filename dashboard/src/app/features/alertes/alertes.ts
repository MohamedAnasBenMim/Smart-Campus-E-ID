import { Component, OnInit, signal, computed, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Alertes as AlertesService } from '../../core/services/alertes';
import { Evenements as EvenementsService } from '../../core/services/evenements';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { Alerte, EvenementAcces, Personne } from '../../core/models';
import { ImageLightbox } from '../../shared/components/image-lightbox/image-lightbox';

const LIBELLES_ALERTE: Record<string, { label: string; icone: string }> = {
  SPOOFING: { label: 'Tentative de spoofing', icone: 'gpp_bad' },
  ACCES_NON_AUTORISE: { label: 'Personne inconnue', icone: 'person_off' },
  ACCES_INTERDIT: { label: 'Zone non autorisée', icone: 'block' },
  HORAIRE_INTERDIT: { label: 'Hors horaire', icone: 'schedule' },
  PRESENCE_NON_IDENTIFIEE: { label: 'Présence non identifiée', icone: 'visibility_off' },
  IDENTITE_A_CONFIRMER: { label: 'Identité à confirmer', icone: 'help' },
};

const LIBELLES_ROLE: Record<string, string> = {
  SURVEILLANT: 'Surveillant',
  DIRECTEUR: 'Directeur',
  AGENT_DE_DIRECTION: 'Agent de direction',
  PROF: 'Professeur',
  ELEVE: 'Élève',
  PERSONNEL: 'Personnel',
};

interface DonneesTraitementAlerte {
  alerteId: string;
  type: string;
  libelle: string;
  horodatage: string;
  capturePhoto?: string;
  personneProposeeNom?: string; // uniquement pour IDENTITE_A_CONFIRMER
}

type Etape = 'choix' | 'selection_personne' | 'enrolement' | 'commentaire';

// ============================================================
// Dialogue de traitement — SPÉCIALISÉ selon le type d'alerte.
//
// IDENTITE_A_CONFIRMER et ACCES_NON_AUTORISE proposent des actions
// qui exploitent l'embedding conservé côté backend pour améliorer la
// reconnaissance — les autres types gardent le simple commentaire
// libre d'origine.
// ============================================================
@Component({
  selector: 'app-traiter-alerte-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
  ],
  template: `
    <h2 mat-dialog-title>Traiter l'alerte</h2>

    <mat-dialog-content>
      <p class="alerte-recap">{{ data.libelle }} — {{ data.horodatage | date: 'dd/MM/yyyy HH:mm' }}</p>

      @if (data.capturePhoto) {
        <div class="capture-wrapper">
          <img [src]="data.capturePhoto" alt="Capture au moment de l'alerte" class="capture-preview" />
          <button type="button" class="bouton-agrandir" (click)="agrandir()" aria-label="Agrandir la capture">
            <mat-icon>zoom_in</mat-icon>
          </button>
        </div>
      }

      <!-- ============ IDENTITE_A_CONFIRMER — étape "choix" ============ -->
      @if (data.type === 'IDENTITE_A_CONFIRMER' && etape() === 'choix') {
        <p class="question">Est-ce bien <strong>{{ data.personneProposeeNom }}</strong> ?</p>
        <div class="actions-choix">
          <button mat-flat-button class="btn-primary" (click)="confirmer()">
            <mat-icon>check</mat-icon> Oui, c'est elle
          </button>
          <button mat-stroked-button (click)="etape.set('selection_personne')">
            <mat-icon>close</mat-icon> Non, ce n'est pas elle
          </button>
        </div>
      }

      <!-- ============ ACCES_NON_AUTORISE — étape "choix" ============ -->
      @if (data.type === 'ACCES_NON_AUTORISE' && etape() === 'choix') {
        <p class="question">Reconnaissez-vous cette personne ?</p>
        <div class="actions-choix actions-choix-colonne">
          <button mat-stroked-button (click)="etape.set('selection_personne')">
            <mat-icon>badge</mat-icon> Oui, elle est déjà enrôlée
          </button>
          <button mat-stroked-button (click)="etape.set('enrolement')">
            <mat-icon>person_add</mat-icon> Oui, mais pas encore enrôlée
          </button>
          <button mat-stroked-button (click)="etape.set('commentaire')">
            <mat-icon>help_outline</mat-icon> Non, vraiment inconnue
          </button>
        </div>
      }

      <!-- ============ Sélection d'une personne déjà enrôlée ============ -->
      @if (etape() === 'selection_personne') {
        <p class="question">
          {{ data.type === 'IDENTITE_A_CONFIRMER' ? 'Qui est-ce réellement ?' : 'Quelle personne est-ce ?' }}
        </p>
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Personne</mat-label>
          <mat-select [(ngModel)]="personneSelectionnee" [ngModelOptions]="{ standalone: true }">
            @for (p of personnes; track p.id) {
              <mat-option [value]="p.id">{{ p.nom }} {{ p.prenom }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <div class="actions-choix">
          @if (data.type === 'IDENTITE_A_CONFIRMER') {
            <button mat-button (click)="corrigerSansIdentite()">Je ne sais pas qui c'est</button>
          }
          <button mat-flat-button class="btn-primary" [disabled]="!personneSelectionnee" (click)="validerSelection()">
            Confirmer
          </button>
        </div>
      }

      <!-- ============ Mini-formulaire d'enrôlement depuis l'alerte ============ -->
      @if (etape() === 'enrolement') {
        <p class="question">Enrôler cette personne directement depuis cette capture</p>
        <form [formGroup]="formEnrolement" class="enrol-form">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Nom</mat-label>
            <input matInput formControlName="nom" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Prénom (optionnel)</mat-label>
            <input matInput formControlName="prenom" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Rôle</mat-label>
            <mat-select formControlName="role">
              @for (r of roles; track r.valeur) {
                <mat-option [value]="r.valeur">{{ r.libelle }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
        </form>
        <div class="actions-choix">
          <button
            mat-flat-button
            class="btn-primary"
            [disabled]="formEnrolement.invalid"
            (click)="validerEnrolement()"
          >
            Enrôler cette personne
          </button>
        </div>
      }

      <!-- ============ Commentaire libre — flux classique, inchangé ============ -->
      @if (etape() === 'commentaire') {
        <form [formGroup]="form" class="traiter-form">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Comment avez-vous traité cette alerte ?</mat-label>
            <textarea
              matInput
              formControlName="commentaire"
              rows="4"
              placeholder="ex. Vérifié sur place, il s'agissait d'un visiteur accompagné par le directeur."
            ></textarea>
          </mat-form-field>
        </form>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      @if (etape() === 'commentaire') {
        <button mat-flat-button class="btn-primary" [disabled]="form.invalid" (click)="soumettreCommentaire()">
          Confirmer le traitement
        </button>
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .alerte-recap {
        color: var(--color-text-muted);
        font-size: 0.85rem;
        margin: -0.5rem 0 1rem;
      }
      .capture-wrapper {
        position: relative;
        margin-bottom: 1rem;
      }
      .capture-preview {
        width: 100%;
        max-height: 220px;
        object-fit: cover;
        border-radius: 10px;
        display: block;
        border: 1px solid var(--color-border);
      }
      .bouton-agrandir {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 8px;
        background: rgba(0, 0, 0, 0.55);
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition:
          background-color 0.15s ease,
          transform 0.15s ease;

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
        }

        &:hover {
          background: rgba(0, 0, 0, 0.75);
          transform: scale(1.05);
        }
      }
      .question {
        font-weight: 600;
        color: var(--color-text);
        margin: 0 0 1rem;
      }
      .actions-choix {
        display: flex;
        justify-content: flex-end;
        gap: 0.6rem;
        margin-top: 0.5rem;
      }
      .actions-choix-colonne {
        flex-direction: column;
        align-items: stretch;
      }
      .actions-choix-colonne button {
        justify-content: flex-start;
      }
      .traiter-form,
      .enrol-form {
        min-width: 380px;
        display: flex;
        flex-direction: column;
      }
      .full-width {
        width: 100%;
      }
    `,
  ],
})
export class TraiterAlerteDialog {
  form: FormGroup;
  formEnrolement: FormGroup;

  etape = signal<Etape>('commentaire'); // valeur temporaire, corrigée dans le constructeur ci-dessous
  personneSelectionnee: string | null = null;
  personnes: Personne[] = [];

  roles = Object.entries(LIBELLES_ROLE).map(([valeur, libelle]) => ({ valeur, libelle }));

  constructor(
    private fb: FormBuilder,
    private alertesService: AlertesService,
    private personnesService: PersonnesService,
    private dialog: MatDialog,
    public dialogRef: MatDialogRef<TraiterAlerteDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: DonneesTraitementAlerte,
  ) {
    this.form = this.fb.group({
      commentaire: ['', [Validators.required, Validators.minLength(5)]],
    });

    this.formEnrolement = this.fb.group({
      nom: ['', Validators.required],
      prenom: [''],
      role: ['ELEVE', Validators.required],
    });

    this.personnesService.lister().subscribe((p) => (this.personnes = p));

    // Corrige la valeur temporaire posée à la déclaration du champ —
    // ici, this.data est bien assigné (paramètre du constructeur).
    this.etape.set(this.etapeInitiale());
  }

  private etapeInitiale(): Etape {
    if (this.data.type === 'IDENTITE_A_CONFIRMER' || this.data.type === 'ACCES_NON_AUTORISE') {
      return 'choix';
    }
    return 'commentaire';
  }

  agrandir(): void {
    if (!this.data.capturePhoto) return;
    this.dialog.open(ImageLightbox, {
      panelClass: 'lightbox-panel',
      backdropClass: 'lightbox-backdrop',
      maxWidth: '95vw',
      data: { imageUrl: this.data.capturePhoto, legende: this.data.libelle },
    });
  }

  // ---- IDENTITE_A_CONFIRMER : "oui, c'est elle" ----
  confirmer(): void {
    this.alertesService.confirmerIdentite(this.data.alerteId).subscribe(() => this.dialogRef.close(true));
  }

  // ---- IDENTITE_A_CONFIRMER : "non" + "je ne sais pas qui c'est" ----
  corrigerSansIdentite(): void {
    this.alertesService.corrigerIdentite(this.data.alerteId).subscribe(() => this.dialogRef.close(true));
  }

  // ---- Sélection d'une personne existante — utilisé par les 2 types ----
  validerSelection(): void {
    if (!this.personneSelectionnee) return;

    const appel$ =
      this.data.type === 'IDENTITE_A_CONFIRMER'
        ? this.alertesService.corrigerIdentite(this.data.alerteId, this.personneSelectionnee)
        : this.alertesService.associerPersonne(this.data.alerteId, this.personneSelectionnee);

    appel$.subscribe(() => this.dialogRef.close(true));
  }

  // ---- ACCES_NON_AUTORISE : enrôlement direct depuis l'alerte ----
  validerEnrolement(): void {
    if (this.formEnrolement.invalid) return;
    const { nom, prenom, role } = this.formEnrolement.value;
    this.alertesService
      .enrolerDepuisAlerte(this.data.alerteId, nom, prenom || null, role)
      .subscribe(() => this.dialogRef.close(true));
  }

  // ---- Flux classique, inchangé ----
  soumettreCommentaire(): void {
    if (this.form.invalid) return;
    this.alertesService.marquerTraitee(this.data.alerteId, this.form.value.commentaire).subscribe(() => {
      this.dialogRef.close(true);
    });
  }
}

// ============================================================
// Page principale
// ============================================================
@Component({
  selector: 'app-alertes',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './alertes.html',
  styleUrl: './alertes.scss',
})
export class AlertesPage implements OnInit {
  alertes = signal<Alerte[]>([]);
  evenements = signal<EvenementAcces[]>([]);
  personnes = signal<Personne[]>([]);
  chargement = signal(true);
  filtre = signal<'NON_TRAITEE' | 'TOUTES'>('NON_TRAITEE');

  constructor(
    private alertesService: AlertesService,
    private evenementsService: EvenementsService,
    private personnesService: PersonnesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  get alertesAffichees(): Alerte[] {
    const toutes = [...this.alertes()].sort(
      (a, b) => new Date(b.horodatage).getTime() - new Date(a.horodatage).getTime(),
    );
    return this.filtre() === 'NON_TRAITEE' ? toutes.filter((a) => a.statut === 'NON_TRAITEE') : toutes;
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.evenementsService.lister().subscribe((e) => this.evenements.set(e));
    this.alertesService.lister().subscribe({
      next: (alertes) => {
        this.alertes.set(alertes);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  libelle(type: string): string {
    return LIBELLES_ALERTE[type]?.label ?? type;
  }

  icone(type: string): string {
    return LIBELLES_ALERTE[type]?.icone ?? 'error_outline';
  }

  /** Nom de la personne proposée par le système — uniquement pertinent
   * pour IDENTITE_A_CONFIRMER (retrouvée via l'événement lié à l'alerte). */
  private nomPersonneProposee(alerte: Alerte): string | undefined {
    const evt = this.evenements().find((e) => e.id === alerte.evenementId);
    if (!evt?.personneId) return undefined;
    const p = this.personnes().find((x) => x.id === evt.personneId);
    return p ? `${p.nom} ${p.prenom ?? ''}`.trim() : undefined;
  }

  agrandir(alerte: Alerte): void {
    if (!alerte.capturePhoto) return;
    this.dialog.open(ImageLightbox, {
      panelClass: 'lightbox-panel',
      backdropClass: 'lightbox-backdrop',
      maxWidth: '95vw',
      data: { imageUrl: alerte.capturePhoto, legende: this.libelle(alerte.type) },
    });
  }

  ouvrirTraitement(alerte: Alerte): void {
    const ref = this.dialog.open(TraiterAlerteDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: {
        alerteId: alerte.id,
        type: alerte.type,
        libelle: this.libelle(alerte.type),
        horodatage: alerte.horodatage,
        capturePhoto: alerte.capturePhoto,
        personneProposeeNom: this.nomPersonneProposee(alerte),
      },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) {
        this.snackBar.open('Alerte traitée avec succès.', 'Fermer', { duration: 3000 });
        this.charger();
      }
    });
  }
}
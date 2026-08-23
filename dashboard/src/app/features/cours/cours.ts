import { Component, OnInit, signal, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CoursService } from '../../core/services/cours';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { Zones as ZonesService } from '../../core/services/zones';
import { ClassesService } from '../../core/services/classes';
import { Cours, Personne, Zone, Classe } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

const JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI'];

interface DonneesCreationCours {
  profs: Personne[];
  classes: Classe[];
  zones: Zone[];
  coursExistant?: Cours; // présent = mode modification
}

// ============================================================
// Dialogue de création ET modification
// ============================================================
@Component({
  selector: 'app-creer-cours-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ modeModification ? 'Modifier le cours' : 'Nouveau cours' }}</h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="cours-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Nom du cours</mat-label>
          <input matInput formControlName="nom" placeholder="ex. Mathématiques 3ème B" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Professeur</mat-label>
          <mat-select formControlName="profId">
            @for (p of data.profs; track p.id) {
              <mat-option [value]="p.id">{{ p.nom }} {{ p.prenom }}</mat-option>
            }
          </mat-select>
          @if (data.profs.length === 0) {
            <mat-hint>Aucune personne avec le rôle "Professeur" pour l'instant</mat-hint>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Salle (zone)</mat-label>
          <mat-select formControlName="zoneId">
            @for (z of data.zones; track z.id) {
              <mat-option [value]="z.id">{{ z.nom }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Jour de la semaine</mat-label>
          <mat-select formControlName="jourSemaine">
            @for (j of jours; track j) {
              <mat-option [value]="j">{{ j }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <div class="horaires-row">
          <label class="time-field">
            <span>Heure début</span>
            <input type="time" formControlName="heureDebut" />
          </label>
          <label class="time-field">
            <span>Heure fin</span>
            <input type="time" formControlName="heureFin" />
          </label>
        </div>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Classe</mat-label>
          <mat-select formControlName="classeId">
            @for (c of data.classes; track c.id) {
              <mat-option [value]="c.id">{{ c.nom }}</mat-option>
            }
          </mat-select>
          @if (data.classes.length === 0) {
            <mat-hint>Créez d'abord une classe, dans la page "Classes"</mat-hint>
          }
        </mat-form-field>
      </form>

      @if (erreur()) {
        <div class="message-erreur">
          <mat-icon>error_outline</mat-icon>
          {{ erreur() }}
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button mat-flat-button class="btn-primary" [disabled]="form.invalid" (click)="soumettre()">
        {{ modeModification ? 'Enregistrer les modifications' : 'Créer le cours' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .cours-form {
        display: flex;
        flex-direction: column;
        min-width: 400px;
      }
      .full-width {
        width: 100%;
      }
      .horaires-row {
        display: flex;
        gap: 1rem;
        margin: 0.25rem 0 1rem;
      }
      .time-field {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        font-size: 0.8rem;
        color: var(--color-text-muted);
      }
      .time-field input {
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 0.6rem 0.7rem;
        font-family: inherit;
        font-size: 0.95rem;
        background: var(--color-bg);
        color: var(--color-text);
      }
      .message-erreur {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        background: #fbeaec;
        color: #d64550;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        font-size: 0.85rem;
        margin-top: 0.5rem;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
          flex-shrink: 0;
        }
      }
    `,
  ],
})
export class CreerCoursDialog {
  form: FormGroup;
  jours = JOURS;
  modeModification: boolean;
  erreur = signal<string | null>(null);

  constructor(
    private fb: FormBuilder,
    private coursService: CoursService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<CreerCoursDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: DonneesCreationCours,
  ) {
    this.modeModification = !!data?.coursExistant;
    const c = data?.coursExistant;

    this.form = this.fb.group({
      nom: [c?.nom ?? '', Validators.required],
      classeId: [c?.classeId ?? '', Validators.required],
      profId: [c?.profId ?? '', Validators.required],
      zoneId: [c?.zoneId ?? '', Validators.required],
      jourSemaine: [c?.jourSemaine ?? 'LUNDI', Validators.required],
      heureDebut: [c?.heureDebut?.substring(0, 5) ?? '08:00', Validators.required],
      heureFin: [c?.heureFin?.substring(0, 5) ?? '09:00', Validators.required],
    });
  }

  soumettre(): void {
    if (this.form.invalid) return;
    this.erreur.set(null);

    const appel$ = this.modeModification
      ? this.coursService.modifier(this.data.coursExistant!.id, this.form.value)
      : this.coursService.creer(this.form.value);

    appel$.subscribe({
      next: () => this.dialogRef.close(true),
      error: (err) => {
        const message = err?.error?.message ?? "Une erreur est survenue, le cours n'a pas pu être enregistré.";
        this.erreur.set(message);
        this.snackBar.open(message, 'Fermer', { duration: 6000 });
      },
    });
  }
}

// ============================================================
// Page principale
// ============================================================
@Component({
  selector: 'app-cours',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './cours.html',
  styleUrl: './cours.scss',
})
export class CoursPage implements OnInit {
  cours = signal<Cours[]>([]);
  personnes = signal<Personne[]>([]);
  zones = signal<Zone[]>([]);
  classes = signal<Classe[]>([]);
  chargement = signal(true);

  constructor(
    private coursService: CoursService,
    private personnesService: PersonnesService,
    private zonesService: ZonesService,
    private classesService: ClassesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.zonesService.lister().subscribe((z) => this.zones.set(z));
    this.classesService.lister().subscribe((c) => this.classes.set(c));
    this.coursService.lister().subscribe({
      next: (cours) => {
        this.cours.set(cours);
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

  nomClasse(id: string): string {
    return this.classes().find((c) => c.id === id)?.nom ?? 'Classe inconnue';
  }

  ouvrirCreation(): void {
    const ref = this.dialog.open(CreerCoursDialog, {
      width: '500px',
      panelClass: 'app-dialog',
      data: {
        profs: this.personnes().filter((p) => p.role === 'PROF'),
        classes: this.classes(),
        zones: this.zones(),
      },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) this.charger();
    });
  }

  ouvrirModification(cours: Cours): void {
    const ref = this.dialog.open(CreerCoursDialog, {
      width: '500px',
      panelClass: 'app-dialog',
      data: {
        profs: this.personnes().filter((p) => p.role === 'PROF'),
        classes: this.classes(),
        zones: this.zones(),
        coursExistant: cours,
      },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) {
        this.snackBar.open('Cours modifié.', 'Fermer', { duration: 3000 });
        this.charger();
      }
    });
  }

  supprimer(cours: Cours): void {
    const ref = this.dialog.open(ConfirmDialog, {
      width: '400px',
      panelClass: 'app-dialog',
      data: {
        titre: 'Supprimer ce cours ?',
        message: `"${cours.nom}" sera définitivement supprimé, ainsi que son historique de présence associé.`,
        labelConfirmer: 'Supprimer',
        dangereux: true,
      },
    });

    ref.afterClosed().subscribe((confirme) => {
      if (!confirme) return;
      this.coursService.supprimer(cours.id).subscribe(() => {
        this.snackBar.open('Cours supprimé.', 'Fermer', { duration: 3000 });
        this.charger();
      });
    });
  }
}
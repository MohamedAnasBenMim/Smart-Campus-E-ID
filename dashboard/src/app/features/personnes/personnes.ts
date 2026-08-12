import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { Personne } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

const LIBELLES_ROLE: Record<string, string> = {
  SURVEILLANT: 'Surveillant',
  DIRECTEUR: 'Directeur',
  AGENT_DE_DIRECTION: 'Agent de direction',
  PROF: 'Professeur',
  ELEVE: 'Élève',
  PERSONNEL: 'Personnel',
};

// ============================================================
// Dialogue d'enrôlement — défini ici, spécifique à cette page
// ============================================================
@Component({
  selector: 'app-enroler-personne-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>Enrôler une personne</h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="enrol-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Nom</mat-label>
          <input matInput formControlName="nom" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Prénom (optionnel)</mat-label>
          <input matInput formControlName="prenom" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Email (optionnel)</mat-label>
          <input matInput formControlName="email" type="email" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Téléphone (optionnel)</mat-label>
          <input matInput formControlName="telephone" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Rôle</mat-label>
          <mat-select formControlName="role">
            @for (r of roles; track r.valeur) {
              <mat-option [value]="r.valeur">{{ r.libelle }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <label class="photo-picker">
          <input type="file" accept="image/*" multiple (change)="onFichiers($event)" hidden />
          <mat-icon>add_a_photo</mat-icon>
          <span>{{ photos().length === 0 ? 'Ajouter des photos (3-5 recommandées)' : photos().length + ' photo(s) sélectionnée(s)' }}</span>
        </label>

        @if (apercus().length > 0) {
          <div class="apercus">
            @for (url of apercus(); track url) {
              <img [src]="url" alt="Aperçu" />
            }
          </div>
        }
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button
        mat-flat-button
        class="btn-primary"
        [disabled]="form.invalid || photos().length === 0 || enCours()"
        (click)="soumettre()"
      >
        {{ enCours() ? 'Enrôlement...' : 'Enrôler' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .enrol-form {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        min-width: 360px;
      }
      .full-width {
        width: 100%;
      }
      .photo-picker {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        border: 1.5px dashed var(--color-border);
        border-radius: 10px;
        padding: 0.9rem 1rem;
        cursor: pointer;
        color: var(--color-text-muted);
        font-size: 0.88rem;
        transition: border-color 0.15s ease;

        &:hover {
          border-color: var(--color-accent);
        }

        mat-icon {
          color: var(--color-accent);
        }
      }
      .apercus {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.75rem;
        flex-wrap: wrap;
      }
      .apercus img {
        width: 56px;
        height: 56px;
        object-fit: cover;
        border-radius: 8px;
        border: 1px solid var(--color-border);
      }
    `,
  ],
})
export class EnrolerPersonneDialog {
  roles = Object.entries(LIBELLES_ROLE).map(([valeur, libelle]) => ({ valeur, libelle }));

  form: FormGroup;
  photos = signal<File[]>([]);
  apercus = signal<string[]>([]);
  enCours = signal(false);

  constructor(
    private fb: FormBuilder,
    private personnesService: PersonnesService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<EnrolerPersonneDialog, boolean>,
  ) {
    this.form = this.fb.group({
      nom: ['', Validators.required],
      prenom: [''],
      email: ['', Validators.email],
      telephone: [''],
      role: ['ELEVE', Validators.required],
    });
  }

  onFichiers(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files) return;
    const fichiers = Array.from(input.files);
    this.photos.set(fichiers);
    this.apercus.set(fichiers.map((f) => URL.createObjectURL(f)));
  }

  soumettre(): void {
    if (this.form.invalid || this.photos().length === 0) return;

    this.enCours.set(true);
    const formData = new FormData();
    const valeurs = this.form.value;
    formData.append('nom', valeurs.nom);
    if (valeurs.prenom) formData.append('prenom', valeurs.prenom);
    if (valeurs.email) formData.append('email', valeurs.email);
    if (valeurs.telephone) formData.append('telephone', valeurs.telephone);
    formData.append('role', valeurs.role);
    this.photos().forEach((f) => formData.append('images', f));

    this.personnesService.creer(formData).subscribe({
      next: () => {
        this.enCours.set(false);
        this.snackBar.open('Personne enrôlée avec succès.', 'Fermer', { duration: 3000 });
        this.dialogRef.close(true);
      },
      error: () => {
        this.enCours.set(false);
        this.snackBar.open("Erreur lors de l'enrôlement.", 'Fermer', { duration: 4000 });
      },
    });
  }
}

// ============================================================
// Page principale
// ============================================================
@Component({
  selector: 'app-personnes',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './personnes.html',
  styleUrl: './personnes.scss',
})
export class PersonnesPage implements OnInit {
  personnes = signal<Personne[]>([]);
  chargement = signal(true);

  constructor(
    private personnesService: PersonnesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe({
      next: (personnes) => {
        this.personnes.set(personnes);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  libelleRole(role: string): string {
    return LIBELLES_ROLE[role] ?? role;
  }

  initiales(p: Personne): string {
    return `${p.nom?.[0] ?? ''}${p.prenom?.[0] ?? ''}`.toUpperCase();
  }

  ouvrirEnrolement(): void {
    const ref = this.dialog.open(EnrolerPersonneDialog, { width: '480px' });
    ref.afterClosed().subscribe((succes) => {
      if (succes) this.charger();
    });
  }

  supprimer(personne: Personne): void {
    const ref = this.dialog.open(ConfirmDialog, {
      width: '400px',
      data: {
        titre: 'Supprimer cette personne ?',
        message: `${personne.nom} ${personne.prenom ?? ''} sera définitivement retiré(e) du système. Cette action est irréversible.`,
        labelConfirmer: 'Supprimer',
        dangereux: true,
      },
    });

    ref.afterClosed().subscribe((confirme) => {
      if (!confirme) return;
      this.personnesService.supprimer(personne.id).subscribe(() => {
        this.snackBar.open('Personne supprimée.', 'Fermer', { duration: 3000 });
        this.charger();
      });
    });
  }
}
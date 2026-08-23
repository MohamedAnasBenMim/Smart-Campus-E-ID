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
import { ClassesService } from '../../core/services/classes';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { Classe, Personne } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

// ============================================================
// Dialogue de création
// ============================================================
@Component({
  selector: 'app-creer-classe-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
  ],
  template: `
    <h2 mat-dialog-title>Nouvelle classe</h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="classe-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Nom de la classe</mat-label>
          <input matInput formControlName="nom" placeholder="ex. 3ème B" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Élèves</mat-label>
          <mat-select formControlName="eleveIds" multiple>
            @for (e of eleves; track e.id) {
              <mat-option [value]="e.id">{{ e.nom }} {{ e.prenom }}</mat-option>
            }
          </mat-select>
          @if (eleves.length === 0) {
            <mat-hint>Aucune personne avec le rôle "Élève" pour l'instant</mat-hint>
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
        Créer la classe
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .classe-form {
        display: flex;
        flex-direction: column;
        min-width: 380px;
      }
      .full-width {
        width: 100%;
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
export class CreerClasseDialog {
  form: FormGroup;
  eleves: Personne[] = [];
  erreur = signal<string | null>(null);

  constructor(
    private fb: FormBuilder,
    private classesService: ClassesService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<CreerClasseDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: { eleves: Personne[] },
  ) {
    this.eleves = data.eleves;
    this.form = this.fb.group({
      nom: ['', Validators.required],
      eleveIds: [[]],
    });
  }

  soumettre(): void {
    if (this.form.invalid) return;
    this.erreur.set(null);

    this.classesService.creer(this.form.value).subscribe({
      next: () => this.dialogRef.close(true),
      error: (err) => {
        const message = err?.error?.message ?? "Une erreur est survenue, la classe n'a pas pu être créée.";
        this.erreur.set(message);
        this.snackBar.open(message, 'Fermer', { duration: 6000 });
      },
    });
  }
}

// ============================================================
// Dialogue "voir les élèves" — consultation simple, lecture seule
// ============================================================
@Component({
  selector: 'app-voir-eleves-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>{{ data.classe.nom }}</h2>

    <mat-dialog-content>
      @if (data.eleves.length === 0) {
        <p class="vide">Aucun élève dans cette classe.</p>
      } @else {
        <div class="liste-eleves">
          @for (e of data.eleves; track e.id) {
            <div class="eleve-ligne">
              <mat-icon>person</mat-icon>
              {{ e.nom }} {{ e.prenom }}
            </div>
          }
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Fermer</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .vide {
        color: var(--color-text-muted);
      }
      .liste-eleves {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        min-width: 300px;
        max-height: 400px;
        overflow-y: auto;
      }
      .eleve-ligne {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.5rem 0.7rem;
        background: var(--color-bg);
        border-radius: 8px;
        font-size: 0.9rem;
        color: var(--color-text);

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
          color: var(--color-accent);
        }
      }
    `,
  ],
})
export class VoirElevesDialog {
  constructor(
    public dialogRef: MatDialogRef<VoirElevesDialog>,
    @Inject(MAT_DIALOG_DATA) public data: { classe: Classe; eleves: Personne[] },
  ) {}
}

// ============================================================
// Page principale
// ============================================================
@Component({
  selector: 'app-classes',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './classes.html',
  styleUrl: './classes.scss',
})
export class ClassesPage implements OnInit {
  classes = signal<Classe[]>([]);
  personnes = signal<Personne[]>([]);
  chargement = signal(true);

  constructor(
    private classesService: ClassesService,
    private personnesService: PersonnesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.classesService.lister().subscribe({
      next: (classes) => {
        this.classes.set(classes);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  elevesDe(classe: Classe): Personne[] {
    return this.personnes().filter((p) => classe.eleveIds?.includes(p.id));
  }

  ouvrirCreation(): void {
    const ref = this.dialog.open(CreerClasseDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: { eleves: this.personnes().filter((p) => p.role === 'ELEVE') },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) this.charger();
    });
  }

  voirEleves(classe: Classe): void {
    this.dialog.open(VoirElevesDialog, {
      width: '400px',
      panelClass: 'app-dialog',
      data: { classe, eleves: this.elevesDe(classe) },
    });
  }

  supprimer(classe: Classe): void {
    const ref = this.dialog.open(ConfirmDialog, {
      width: '400px',
      panelClass: 'app-dialog',
      data: {
        titre: 'Supprimer cette classe ?',
        message: `"${classe.nom}" sera définitivement supprimée. Les cours qui y sont rattachés resteront, mais sans classe valide.`,
        labelConfirmer: 'Supprimer',
        dangereux: true,
      },
    });

    ref.afterClosed().subscribe((confirme) => {
      if (!confirme) return;
      this.classesService.supprimer(classe.id).subscribe(() => {
        this.snackBar.open('Classe supprimée.', 'Fermer', { duration: 3000 });
        this.charger();
      });
    });
  }
}
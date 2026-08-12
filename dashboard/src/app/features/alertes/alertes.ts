import { Component, OnInit, signal, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Alertes as AlertesService } from '../../core/services/alertes';
import { Alerte } from '../../core/models';

const LIBELLES_ALERTE: Record<string, { label: string; icone: string }> = {
  SPOOFING: { label: 'Tentative de spoofing', icone: 'gpp_bad' },
  ACCES_NON_AUTORISE: { label: 'Personne inconnue', icone: 'person_off' },
  ACCES_INTERDIT: { label: 'Zone non autorisée', icone: 'block' },
  HORAIRE_INTERDIT: { label: 'Hors horaire', icone: 'schedule' },
  PRESENCE_NON_IDENTIFIEE: { label: 'Présence non identifiée', icone: 'visibility_off' },
  IDENTITE_A_CONFIRMER: { label: 'Identité à confirmer', icone: 'help' },
};

// ============================================================
// Dialogue de traitement — le formulaire demandé par l'encadrant :
// l'admin/surveillant doit EXPLIQUER comment il a géré l'alerte,
// pas juste cocher "traité".
// ============================================================
@Component({
  selector: 'app-traiter-alerte-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  template: `
    <h2 mat-dialog-title>Traiter l'alerte</h2>

    <mat-dialog-content>
      <p class="alerte-recap">{{ data.libelle }} — {{ data.horodatage | date: 'dd/MM/yyyy HH:mm' }}</p>

      @if (data.capturePhoto) {
        <img [src]="data.capturePhoto" alt="Capture au moment de l'alerte" class="capture-preview" />
      }

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
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button mat-flat-button class="btn-primary" [disabled]="form.invalid" (click)="soumettre()">
        Confirmer le traitement
      </button>
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
      .capture-preview {
        width: 100%;
        max-height: 220px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid var(--color-border);
      }
      .traiter-form {
        min-width: 380px;
      }
      .full-width {
        width: 100%;
      }
    `,
  ],
})
export class TraiterAlerteDialog {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private alertesService: AlertesService,
    public dialogRef: MatDialogRef<TraiterAlerteDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: { alerteId: string; libelle: string; horodatage: string; capturePhoto?: string },
  ) {
    this.form = this.fb.group({
      commentaire: ['', [Validators.required, Validators.minLength(5)]],
    });
  }

  soumettre(): void {
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
  chargement = signal(true);
  filtre = signal<'NON_TRAITEE' | 'TOUTES'>('NON_TRAITEE');

  constructor(
    private alertesService: AlertesService,
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

  ouvrirTraitement(alerte: Alerte): void {
    const ref = this.dialog.open(TraiterAlerteDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: {
        alerteId: alerte.id,
        libelle: this.libelle(alerte.type),
        horodatage: alerte.horodatage,
        capturePhoto: alerte.capturePhoto,
      },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) {
        this.snackBar.open('Alerte marquée comme traitée.', 'Fermer', { duration: 3000 });
        this.charger();
      }
    });
  }
}
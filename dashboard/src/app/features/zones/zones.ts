import { Component, OnInit, signal, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Zones as ZonesService } from '../../core/services/zones';
import { Zone } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

interface DonneesDialogueZone {
  zoneExistante?: Zone; // présente = mode modification ; absente = mode création
}

// ============================================================
// Dialogue de création ET modification — le même formulaire sert
// pour les deux : s'il reçoit une zone existante, il se pré-remplit
// et appelle modifier() au lieu de creer().
// ============================================================
@Component({
  selector: 'app-creer-zone-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>{{ modeModification ? 'Modifier la zone' : 'Nouvelle zone' }}</h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="zone-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Nom de la zone</mat-label>
          <input matInput formControlName="nom" placeholder="ex. Labo Info" />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Description (optionnel)</mat-label>
          <textarea matInput formControlName="description" rows="3" placeholder="ex. Salle informatique, bâtiment B"></textarea>
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
        {{ modeModification ? 'Enregistrer les modifications' : 'Créer la zone' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .zone-form {
        display: flex;
        flex-direction: column;
        min-width: 360px;
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
export class CreerZoneDialog {
  form: FormGroup;
  modeModification: boolean;
  erreur = signal<string | null>(null);

  constructor(
    private fb: FormBuilder,
    private zonesService: ZonesService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<CreerZoneDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: DonneesDialogueZone,
  ) {
    this.modeModification = !!data?.zoneExistante;

    this.form = this.fb.group({
      nom: [data?.zoneExistante?.nom ?? '', Validators.required],
      description: [data?.zoneExistante?.description ?? ''],
    });
  }

  soumettre(): void {
    if (this.form.invalid) return;
    this.erreur.set(null);

    const appel$ = this.modeModification
      ? this.zonesService.modifier(this.data.zoneExistante!.id, this.form.value)
      : this.zonesService.creer(this.form.value);

    appel$.subscribe({
      next: () => this.dialogRef.close(true),
      error: (err) => {
        const message = err?.error?.message ?? 'Une erreur est survenue.';
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
  selector: 'app-zones',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './zones.html',
  styleUrl: './zones.scss',
})
export class ZonesPage implements OnInit {
  zones = signal<Zone[]>([]);
  chargement = signal(true);

  constructor(
    private zonesService: ZonesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.zonesService.lister().subscribe({
      next: (zones) => {
        this.zones.set(zones);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  ouvrirCreation(): void {
    const ref = this.dialog.open(CreerZoneDialog, { width: '480px', panelClass: 'app-dialog' });
    ref.afterClosed().subscribe((succes) => {
      if (succes) this.charger();
    });
  }

  ouvrirModification(zone: Zone): void {
    const ref = this.dialog.open(CreerZoneDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: { zoneExistante: zone },
    });
    ref.afterClosed().subscribe((succes) => {
      if (succes) {
        this.snackBar.open('Zone modifiée.', 'Fermer', { duration: 3000 });
        this.charger();
      }
    });
  }

  supprimer(zone: Zone): void {
    const ref = this.dialog.open(ConfirmDialog, {
      width: '400px',
      panelClass: 'app-dialog',
      data: {
        titre: 'Supprimer cette zone ?',
        message: `"${zone.nom}" sera définitivement supprimée. Les règles d'accès associées à cette zone ne fonctionneront plus.`,
        labelConfirmer: 'Supprimer',
        dangereux: true,
      },
    });

    ref.afterClosed().subscribe((confirme) => {
      if (!confirme) return;
      this.zonesService.supprimer(zone.id).subscribe(() => {
        this.snackBar.open('Zone supprimée.', 'Fermer', { duration: 3000 });
        this.charger();
      });
    });
  }
}
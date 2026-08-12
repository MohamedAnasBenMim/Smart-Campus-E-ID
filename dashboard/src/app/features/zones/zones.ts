import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Zones as ZonesService } from '../../core/services/zones';
import { Zone } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

// ============================================================
// Dialogue de création — simple, propre à cette page
// ============================================================
@Component({
  selector: 'app-creer-zone-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  template: `
    <h2 mat-dialog-title>Nouvelle zone</h2>

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
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button mat-flat-button class="btn-primary" [disabled]="form.invalid" (click)="soumettre()">
        Créer la zone
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
    `,
  ],
})
export class CreerZoneDialog {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private zonesService: ZonesService,
    public dialogRef: MatDialogRef<CreerZoneDialog, boolean>,
  ) {
    this.form = this.fb.group({
      nom: ['', Validators.required],
      description: [''],
    });
  }

  soumettre(): void {
    if (this.form.invalid) return;
    this.zonesService.creer(this.form.value).subscribe(() => this.dialogRef.close(true));
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
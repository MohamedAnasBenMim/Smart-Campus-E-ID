import { Component, Inject } from '@angular/core';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface ConfirmDialogData {
  titre: string;
  message: string;
  labelConfirmer?: string; // "Supprimer" par défaut
  dangereux?: boolean; // true = bouton rouge (suppression), false = bouton normal
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './confirm-dialog.html',
  styleUrl: './confirm-dialog.scss',
})
export class ConfirmDialog {
  constructor(
    private dialogRef: MatDialogRef<ConfirmDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData,
  ) {}

  annuler(): void {
    this.dialogRef.close(false);
  }

  confirmer(): void {
    this.dialogRef.close(true);
  }
}
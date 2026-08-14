import { Component, Inject } from '@angular/core';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

export interface ImageLightboxData {
  imageUrl: string;
  legende?: string;
}

@Component({
  selector: 'app-image-lightbox',
  standalone: true,
  imports: [MatDialogModule, MatIconModule, MatButtonModule],
  templateUrl: './image-lightbox.html',
  styleUrl: './image-lightbox.scss',
})
export class ImageLightbox {
  constructor(
    public dialogRef: MatDialogRef<ImageLightbox>,
    @Inject(MAT_DIALOG_DATA) public data: ImageLightboxData,
  ) {}
}
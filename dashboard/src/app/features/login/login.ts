import { Component, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Auth } from '../../core/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login implements OnInit, OnDestroy {
  form: FormGroup;

  hidePassword = signal(true);
  loading = signal(false);
  errorMessage = signal<string | null>(null);
  now = signal(new Date());

  formattedTime = computed(() => this.now().toLocaleTimeString('fr-FR'));
  formattedDate = computed(() => {
    const d = this.now();
    const jour = d.toLocaleDateString('fr-FR', { weekday: 'long' });
    const reste = d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    return `${jour.charAt(0).toUpperCase() + jour.slice(1)} ${reste}`;
  });

  private clockInterval?: ReturnType<typeof setInterval>;

  constructor(
    private fb: FormBuilder,
    private auth: Auth,
    private router: Router,
  ) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      motDePasse: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.clockInterval = setInterval(() => this.now.set(new Date()), 1000);
  }

  ngOnDestroy(): void {
    if (this.clockInterval) clearInterval(this.clockInterval);
  }

  submit(): void {
    if (this.form.invalid) return;

    this.loading.set(true);
    this.errorMessage.set(null);

    const { email, motDePasse } = this.form.value;
    this.auth.login(email!, motDePasse!).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/']);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('Email ou mot de passe incorrect.');
      },
    });
  }
}
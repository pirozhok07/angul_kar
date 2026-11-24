import {
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ExportService } from '../export.service';
import { U } from '@angular/cdk/keycodes';

@Component({
  imports: [CommonModule],
  selector: 'app-export-list',
  standalone: true,
  styleUrl: './export-list.scss',
  templateUrl: './export-list.html',
})
export class ExportList implements OnInit {
  
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(ExportService);

  tournamentId = 0;

  loading = signal(true);
  error = signal('');

  ngOnInit(): void {
    const id = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Некорректный ID турнира');
      return;
    }

    this.tournamentId = id;
    this.loading = signal(false);
  }
  categories(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.categories(this.tournamentId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = 'categories.xlsx';
        link.click();

        window.URL.revokeObjectURL(url);
        this.loading.set(false);
      },
      error: (err: any) => {
        this.error.set('Не удалось загрузить файл');
        this.loading.set(false);
      }
    });
  }

  kata(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.kata(this.tournamentId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = 'kata.xlsx';
        link.click();

        window.URL.revokeObjectURL(url);
        this.loading.set(false);
      },
      error: (err: any) => {
        this.error.set('Не удалось загрузить файл');
        this.loading.set(false);
      }
    });
  }

  kumite(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.kumite(this.tournamentId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = 'kumite.xlsx';
        link.click();

        window.URL.revokeObjectURL(url);
        this.loading.set(false);
      },
      error: (err: any) => {
        this.error.set('Не удалось загрузить файл');
        this.loading.set(false);
      }
    });
  }

  results(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.results(this.tournamentId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = 'kumite.xlsx';
        link.click();

        window.URL.revokeObjectURL(url);
        this.loading.set(false);
      },
      error: (err: any) => {
        this.error.set('Не удалось загрузить файл');
        this.loading.set(false);
      }
    });
  }
}

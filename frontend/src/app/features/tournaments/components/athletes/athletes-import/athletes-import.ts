import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import {
  AthletesService,
  ImportPreview
} from '../athletes.service';

@Component({
  selector: 'app-athletes-import',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './athletes-import.html',
  styleUrl: './athletes-import.scss'
})
export class AthletesImport implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(AthletesService);

  tournamentId = 0;

  file = signal<File | null>(null);
  preview = signal<ImportPreview | null>(null);
  loading = signal(false);
  error = signal('');
  success = signal('');

  ngOnInit(): void {
    const id = Number(
      this.route.parent?.parent?.snapshot.paramMap.get('id')
    );

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Не удалось определить турнир');
      return;
    }

    this.tournamentId = id;
  }

  selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const selected = input.files?.[0] ?? null;

    this.preview.set(null);
    this.error.set('');
    this.success.set('');

    if (!selected) {
      this.file.set(null);
      return;
    }

    if (!selected.name.toLowerCase().endsWith('.xlsx')) {
      this.file.set(null);
      this.error.set('Выберите файл формата .xlsx');
      input.value = '';
      return;
    }

    this.file.set(selected);
  }

  downloadTemplate(): void {
    this.service.downloadTemplate(this.tournamentId).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = 'athletes_template.xlsx';
        link.click();

        URL.revokeObjectURL(url);
      },
      error: () => {
        this.error.set('Не удалось скачать шаблон');
      }
    });
  }

  previewImport(): void {
    const file = this.file();

    if (!file) {
      this.error.set('Сначала выберите Excel-файл');
      return;
    }

    this.loading.set(true);
    this.error.set('');
    this.success.set('');
    this.preview.set(null);

    this.service.previewImport(this.tournamentId, file).subscribe({
      next: result => {
        this.preview.set(result);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(
          err.error?.detail?.message ||
          err.error?.detail ||
          'Не удалось проверить файл'
        );
        this.loading.set(false);
      }
    });
  }

  confirmImport(): void {
    const file = this.file();
    const preview = this.preview();

    if (!file || !preview || preview.invalid > 0 || preview.valid === 0) {
      this.error.set('Исправьте ошибки перед импортом');
      return;
    }

    if (!confirm(`Импортировать ${preview.valid} спортсменов?`)) {
      return;
    }

    this.loading.set(true);
    this.error.set('');

    this.service.confirmImport(this.tournamentId, file).subscribe({
      next: result => {
        this.success.set(result.message);
        this.preview.set(null);
        this.file.set(null);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(
          err.error?.detail?.message ||
          'Импорт не выполнен. Проверьте файл и повторите попытку.'
        );
        this.loading.set(false);
      }
    });
  }
}

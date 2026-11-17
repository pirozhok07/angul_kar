import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

import {
  CategoriesService,
  Category,
  CategoryField
} from '../categories.service';

@Component({
  imports: [CommonModule],
  selector: 'app-categories-distribution',
  standalone: true,
  styleUrl: './categories-distribution.scss',
  templateUrl: './categories-distribution.html',
})
export class CategoriesDistribution implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(CategoriesService);

  tournamentId = 0;

  categories = signal<Category[]>([]);
  fields = signal<CategoryField[]>([]);

  preview = signal<any>(null);
  distribution = signal<any>(null);

  loading = signal(false);
  distributing = signal(false);
  error = signal('');
  success = signal('');

  visibleFields = computed(() =>
    this.fields().filter(field => field.name !== 'id')
  );

  ngOnInit(): void {
    const id = Number(this.route.parent?.snapshot.paramMap.get('id'));

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Не удалось определить турнир');
      return;
    }

    this.tournamentId = id;
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.success.set('');

    this.service.getFields(this.tournamentId).subscribe({
      next: fields => {
        this.fields.set(fields);

        this.service.getAll(this.tournamentId).subscribe({
          next: categories => {
            this.categories.set(categories);
            this.loadPreview();
          },
          error: () => {
            this.error.set('Не удалось загрузить категории');
            this.loading.set(false);
          }
        });
      },
      error: () => {
        this.error.set('Не удалось загрузить структуру категорий');
        this.loading.set(false);
      }
    });
  }

  loadPreview(): void {
    this.service.preview(this.tournamentId).subscribe({
      next: result => {
        this.preview.set(result);
        this.loadDistribution();
      },
      error: () => {
        this.error.set('Не удалось сформировать предварительное распределение');
        this.loading.set(false);
      }
    });
  }

  loadDistribution(): void {
    this.service.getDistribution(this.tournamentId).subscribe({
      next: result => {
        this.distribution.set(result);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Не удалось загрузить распределение');
        this.loading.set(false);
      }
    });
  }

  distribute(): void {
    if (this.distributing()) {
      return;
    }

    const confirmed = confirm(
      'Выполнить распределение спортсменов по категориям? Предыдущее распределение будет заменено.'
    );

    if (!confirmed) {
      return;
    }

    this.distributing.set(true);
    this.error.set('');
    this.success.set('');

    this.service.distribute(this.tournamentId).subscribe({
      next: result => {
        this.distributing.set(false);
        this.success.set(
          `Распределение выполнено. Распределено: ${result.distributed_athletes ?? 0}, не распределено: ${result.undistributed_athletes ?? 0}.`
        );

        this.loadDistribution();
      },
      error: err => {
        this.distributing.set(false);
        this.error.set(
          err.error?.detail || 'Не удалось выполнить распределение'
        );
      }
    });
  }

  getCategoryName(categoryId: number): string {
    const category = this.categories().find(item => item.id === categoryId);
    return String(category?.['name'] ?? `Категория ${categoryId}`);
  }

  getAthleteName(athlete: any): string {
    if (!athlete) {
      return '';
    }

    return [athlete.last_name, athlete.first_name, athlete.second_name]
          .filter(Boolean)
          .join(' ');
  }

  getPreviewAthletes(): any[] {
    return this.preview()?.athletes ?? [];
  }

  getPreviewGroups(): any[] {
    return this.preview()?.kata_groups ?? [];
  }

  getDistributionCategories(): any[] {
    return this.distribution()?.categories ?? [];
  }

  getUndistributed(): any[] {
    return this.distribution()?.undistributed ?? [];
  }
}


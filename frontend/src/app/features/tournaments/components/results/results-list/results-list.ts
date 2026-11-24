
import {
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { Results } from '../results.service';


@Component({
  imports: [CommonModule],
  selector: 'app-results-list',
  standalone: true,
  styleUrl: './results-list.scss',
  templateUrl: './results-list.html',
})
export class ResultsList implements OnInit {

  private route = inject(ActivatedRoute);
  private service = inject(Results);

  tournamentId = 0;

  categories = signal<any[]>([]);
  loading = signal(false);
  error = signal('');
  search = signal('');

  totalAthletes = computed(() =>
    this.categories().reduce(
      (total, category) => total + category.results.length,
      0
    )
  );

  visibleCategories = computed(() => {
    const value = this.search().trim().toLowerCase();

    if (!value) {
      return this.categories();
    }

    return this.categories()
      .map(category => ({
        ...category,
        results: category.results.filter((athlete: any) => {
          const fullName =
            `${athlete.last_name} ${athlete.first_name}`.toLowerCase();

          const club = (athlete.club || '').toLowerCase();

          return fullName.includes(value) ||
            club.includes(value);
        })
      }))
      .filter(category =>
        category.category_name.toLowerCase().includes(value) ||
        category.results.length > 0
      );
  });

  ngOnInit(): void {
    const id = Number(
      this.route.parent?.parent?.snapshot.paramMap.get('id')
    );

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Некорректный ID турнира');
      return;
    }

    this.tournamentId = id;
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getResults(this.tournamentId).subscribe({
      next: data => {
        this.categories.set(data || []);
        this.loading.set(false);
      },
      error: err => {
        console.error(err);
        this.error.set('Не удалось загрузить результаты');
        this.loading.set(false);
      }
    });
  }

  medal(place: number): string {
    switch (place) {
      case 1: return '🥇';
      case 2: return '🥈';
      case 3: return '🥉';
      default: return '';
    }
  }

  placeName(place: number): string {
    switch (place) {
      case 1: return '1 место';
      case 2: return '2 место';
      case 3: return '3 место';
      default: return `${place} место`;
    }
  }
}
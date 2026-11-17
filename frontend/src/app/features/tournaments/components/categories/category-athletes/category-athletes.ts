import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CategoriesService } from '../categories.service';


@Component({
  imports: [CommonModule, RouterLink],
  standalone: true,
  selector: 'app-category-athletes',
  styleUrl: './category-athletes.scss',
  templateUrl: './category-athletes.html',
})
export class CategoryAthletes implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(CategoriesService);

  tournamentId = 0;
  categoryId = 0;

  category = signal<any>(null);
  participants = signal<any[]>([]);
  loading = signal(false);
  error = signal('');

  ngOnInit(): void {
    this.tournamentId = Number(
      this.route.parent?.parent?.snapshot.paramMap.get('id')
    );

    this.categoryId = Number(
      this.route.snapshot.paramMap.get('categoryId')
    );

    if (!this.tournamentId || !this.categoryId) {
      this.error.set('Не удалось определить турнир или категорию');
      return;
    }

    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getCategoryAthletes(
      this.tournamentId,
      this.categoryId
    ).subscribe({
      next: result => {
        this.category.set(result.category);
        this.participants.set(result.participants ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Не удалось загрузить спортсменов категории');
        this.loading.set(false);
      }
    });
  }

  getAthleteName(athlete: any): string {
    return athlete.full_name ||
      [
        athlete.last_name,
        athlete.first_name,
        athlete.second_name
      ].filter(Boolean).join(' ');
  }
}


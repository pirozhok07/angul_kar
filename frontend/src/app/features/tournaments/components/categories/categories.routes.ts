import { Routes } from '@angular/router';

import { CategoriesList }  from './categories-list/categories-list';
import { CategoriesDistribution }  from './categories-distribution/categories-distribution';
import { CategoryAthletes }  from './category-athletes/category-athletes';
import { KATA_DRAWS_ROUTES } from'../kata/kata.routes';
import { KataDraw } from'../kata/kata-draw/kata-draw';

export const CATEGORIES_ROUTES: Routes = [
    {
        path: '',
        component: CategoriesList
    },
    {
        path: 'distribution',
        component: CategoriesDistribution
    },
    {
        path: 'kata-draw/:categoryId',
        component: KataDraw
    },
    {
        path: ':categoryId',
        component: CategoryAthletes
    }
];

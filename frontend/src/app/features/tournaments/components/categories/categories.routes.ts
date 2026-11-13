import { Routes } from '@angular/router';

import { CategoriesList }  from './categories-list/categories-list';

export const CATEGORIES_ROUTES: Routes = [
    {
        path: '',
        component: CategoriesList
    }
];

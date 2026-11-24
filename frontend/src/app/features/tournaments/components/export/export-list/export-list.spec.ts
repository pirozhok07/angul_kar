import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExportList } from './export-list';

describe('ExportList', () => {
  let component: ExportList;
  let fixture: ComponentFixture<ExportList>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExportList],
    }).compileComponents();

    fixture = TestBed.createComponent(ExportList);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

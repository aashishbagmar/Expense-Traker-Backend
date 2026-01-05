"""Management command to retrain AI categorizer using correction feedback."""

from django.core.management.base import BaseCommand
from transactions.models import CategoryCorrection
from django.db.models import Count
import pandas as pd
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import re


class Command(BaseCommand):
    help = 'Retrain AI categorizer using user correction feedback'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-corrections',
            type=int,
            default=5,
            help='Minimum number of corrections required before retraining (default: 5 for adaptive learning)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show stats without retraining'
        )

    def handle(self, *args, **options):
        min_corrections = options['min_corrections']
        dry_run = options['dry_run']

        # Fetch all corrections
        corrections = CategoryCorrection.objects.all()
        total_corrections = corrections.count()

        self.stdout.write(f"\n📊 Total corrections logged: {total_corrections}")

        if total_corrections == 0:
            self.stdout.write(self.style.WARNING("No corrections available. Nothing to retrain."))
            return

        # Show category distribution
        category_stats = corrections.values('user_corrected_category').annotate(
            count=Count('id')
        ).order_by('-count')

        self.stdout.write("\n📈 Correction distribution by category:")
        for stat in category_stats:
            self.stdout.write(f"  {stat['user_corrected_category']}: {stat['count']}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n✓ Dry run complete. No retraining performed."))
            return

        if total_corrections < min_corrections:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️ Only {total_corrections} corrections available. "
                    f"Need at least {min_corrections} to retrain. Skipping."
                )
            )
            return

        # Prepare training data from corrections
        data = []
        for correction in corrections:
            data.append({
                'description': correction.description,
                'category': correction.user_corrected_category
            })

        df = pd.DataFrame(data)

        # Remove duplicates
        df = df.drop_duplicates(subset=['description'])

        self.stdout.write(f"\n🔄 Training with {len(df)} unique correction samples...")

        # Preprocess descriptions - keep more lenient for short corrections
        def preprocess_text(text):
            if not isinstance(text, str):
                return ""
            text = text.lower().strip()
            # Only remove common filler words if text is long enough
            if len(text) > 15:
                text = re.sub(r'\b(online|advance|emergency|monthly|for office|for home|personal|with family|charges|payment|bill|expense|fees)\b', '', text)
            # Keep alphanumeric + spaces, but be lenient
            text = re.sub(r'[^a-z0-9\s]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        df['processed'] = df['description'].apply(preprocess_text)

        # Filter out empty descriptions but allow more lenient threshold
        df = df[df['processed'].str.len() > 0]
        
        self.stdout.write(f"   Valid samples after preprocessing: {len(df)}")

        if len(df) < 2:
            self.stdout.write(self.style.ERROR(f"❌ Not enough valid data. Have {len(df)}, need at least 2."))
            return

        # Split data - be lenient with small datasets
        X = df['processed']
        y = df['category']
        
        # For very small datasets, use all data for training
        if len(df) < 5:
            self.stdout.write(f"   Using all {len(df)} samples for training (dataset too small for split)")
            X_train, X_test, y_train, y_test = X, X, y, y
        else:
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )
            except ValueError:
                # If stratify fails due to class imbalance, train without stratification
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )

        # Vectorize
        vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2), min_df=1)
        X_train_vec = vectorizer.fit_transform(X_train)
        X_test_vec = vectorizer.transform(X_test)

        # Train model
        model = LogisticRegression(max_iter=500, class_weight='balanced')
        model.fit(X_train_vec, y_train)

        # Evaluate
        y_pred = model.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)

        self.stdout.write(f"\n✅ Model trained successfully!")
        self.stdout.write(f"📊 Test Accuracy: {accuracy * 100:.2f}%")
        self.stdout.write("\n📋 Classification Report:")
        self.stdout.write(classification_report(y_test, y_pred))

        # Save model
        model_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        model_path = os.path.join(model_dir, 'expense_category_model.pkl')
        vectorizer_path = os.path.join(model_dir, 'tfidf_vectorizer.pkl')

        joblib.dump(model, model_path)
        joblib.dump(vectorizer, vectorizer_path)

        self.stdout.write(self.style.SUCCESS(f"\n💾 Model saved to: {model_path}"))
        self.stdout.write(self.style.SUCCESS(f"💾 Vectorizer saved to: {vectorizer_path}"))
        self.stdout.write(self.style.SUCCESS("\n🎉 Retraining complete! AI will now use corrected categories."))

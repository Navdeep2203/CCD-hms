export default function PageState({
  loading = false,
  error = "",
  onRetry,
  empty = "",
  children,
}) {
  if (loading) {
    return <div className="panel loading">Loading...</div>;
  }

  if (error) {
    return (
      <div className="panel pageState">
        <p>{error}</p>

        {onRetry && (
          <button className="primary" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  }

  if (empty) {
    return <div className="panel pageState emptyState">{empty}</div>;
  }

  return children || null;
}
